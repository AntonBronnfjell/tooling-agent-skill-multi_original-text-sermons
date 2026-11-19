"""Comparison translations -> `translations(version, lang, ref, text)`.

Vendored: `sources/translations/<VER>.vpl.xz` (eBible VPL, one verse per line `BOOK C:V text`, KJV versification).
  version = filename stem, lang from MANIFEST.json; entries whose status is not 'vendored' are skipped.
  Translators' bracket marks (KJV `[was]` italics = added words) are kept as-is. Empty-text lines are skipped, counted.
User CSVs: `sources/user/*.csv`, first line `# version=NAME lang=xx`, then header `ref,text`, then rows;
  `ref` is anything parse_ref accepts. Unparseable refs are skipped, counted, first few printed.
"""
import csv
import json
import lzma
import re
import sys
from pathlib import Path

from otslib import refs

VPL_BOOKS = dict(zip(
    "GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SOL ISA JER LAM EZE DAN "
    "HOS JOE AMO OBA JON MIC NAH HAB ZEP HAG ZEC MAL MAT MAR LUK JOH ACT ROM 1CO 2CO GAL EPH PHI COL 1TH 2TH 1TI "
    "2TI TIT PHM HEB JAM 1PE 2PE 1JO 2JO 3JO JUD REV".split(), refs.BOOKS))
assert len(VPL_BOOKS) == 66

_LINE = re.compile(r"^(\w{3}) (\d+):(\d+) ?(.*)$")
_HDR = re.compile(r"^#\s*version=(\S+)\s+lang=(\S+)\s*$")


def _vendored(sources_dir, out):
    try:
        man = json.loads((sources_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    res = []
    for e in man.get("entries", []):
        p = e.get("path", "")
        if not p.startswith("translations/") or not p.endswith(".vpl.xz"):
            continue
        if e.get("status") != "vendored":
            print(f"translations: {Path(p).name} skipped (status {e.get('status')})", file=out)
            continue
        res.append((Path(p).name[:-len(".vpl.xz")], e.get("lang", ""), sources_dir / p))
    return res


def _load_vpl(conn, version, lang, path):
    rows, empty, bad = [], 0, 0
    with lzma.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            m = _LINE.match(line.rstrip("\r\n"))
            book = VPL_BOOKS.get(m.group(1)) if m else None
            if not book:
                bad += 1
                continue
            text = m.group(4).strip()
            if not text:
                empty += 1
                continue
            rows.append((version, lang, f"{book}.{int(m.group(2))}.{int(m.group(3))}", text))
    conn.executemany("INSERT INTO translations VALUES (?,?,?,?)", rows)
    return len(rows), empty, bad


def _load_csv(conn, path, out):
    with open(path, encoding="utf-8-sig", newline="") as f:
        first = f.readline().strip()
        m = _HDR.match(first)
        if not m:
            print(f"translations: {path.name} skipped (first line must be '# version=NAME lang=xx')", file=out)
            return None
        version, lang = m.groups()
        rd = csv.reader(f)
        header = next(rd, None)
        if [h.strip().lower() for h in header or []] != ["ref", "text"]:
            print(f"translations: {path.name} skipped (header must be 'ref,text')", file=out)
            return None
        rows, bad = [], []
        for r in rd:
            if len(r) < 2 or not r[1].strip():
                if r and any(r):
                    bad.append(r[0])
                continue
            try:
                ref = refs.to_osis(refs.parse_ref(r[0]))
            except refs.RefError:
                bad.append(r[0])
                continue
            rows.append((version, lang, ref, r[1].strip()))
    conn.executemany("INSERT INTO translations VALUES (?,?,?,?)", rows)
    return version, len(rows), bad


def load(conn, sources_dir, out=None):
    out = out or sys.stdout
    sources_dir = Path(sources_dir)
    total = 0
    for version, lang, path in _vendored(sources_dir, out):
        if not path.is_file():
            raise FileNotFoundError(f"translations: {path} is vendored in MANIFEST but missing")
        n, empty, bad = _load_vpl(conn, version, lang, path)
        total += n
        print(f"translations {version} ({lang}): {n} verses, {empty} empty skipped, {bad} unrecognised lines", file=out)
    for path in sorted((sources_dir / "user").glob("*.csv")):
        res = _load_csv(conn, path, out)
        if res is None:
            continue
        version, n, bad = res
        total += n
        print(f"translations {version} (user {path.name}): {n} verses, {len(bad)} unparseable ref(s) skipped", file=out)
        if bad:
            print(f"  first unparseable: {', '.join(repr(b) for b in bad[:5])}", file=out)
    return total
