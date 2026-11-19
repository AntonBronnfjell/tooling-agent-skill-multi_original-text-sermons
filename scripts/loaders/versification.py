"""Versification loader: TVTMS -> `versification` rows for schemes `hebrew` and `lxx`.

# ponytail: only hebrew/lxx schemes; add Vulgate etc. if ever needed. The Expanded
# `Tests` column is not evaluated (SourceType picks the tradition). Starred renumber
# actions (`Renumber verse*`, conditional/uncertain rows) are accepted. Conflicts on one
# source ref are resolved by SourceType rank (Rahlfs `Greek`/`Latin+Greek` over `Greek2`,
# `Greek3`, ...), then file order.
"""
import lzma
import re
from pathlib import Path

from otslib.refs import RefError, parse_ref, to_osis

_TOKEN = re.compile(r"^\*?\s*([0-9A-Za-z]+)\.(\d+):(\w+?)(?:!\w+)?\s*$")
_ACTIONS = {"Renumber verse", "Renumber title"}


def _rank(source_type):
    return 0 if "Greek" in [t.strip() for t in source_type.split("+")] else 1


def _osis(text, chapter_hint=None):
    """'Psa.51:Title' / 'Psa.50:3!a' / 'Psa.13:6a' -> 'Ps.51.0' / 'Ps.50.3' / 'Ps.13.6'."""
    m = _TOKEN.match(text)
    if not m:
        raise RefError(f"cannot parse {text!r}")
    book, chap, verse = m.groups()
    verse = "0" if verse.lower() == "title" else re.sub(r"[a-z]+$", "", verse)
    if not verse.isdigit():
        raise RefError(f"cannot parse {text!r}")
    return to_osis(parse_ref(f"{book}.{chap}:{verse}"))


def _split_cell(cell):
    """Hebrew cells such as 'Psa.51:1,2' or 'Num.25:19; 26:1' -> full per-verse refs."""
    out, book_chap = [], None
    for tok in re.split(r"[;,]", cell):
        tok = tok.strip()
        if not tok:
            continue
        if "." in tok:
            book_chap = tok.rsplit(":", 1)[0] if ":" in tok else tok
        elif ":" in tok:
            book_chap = book_chap.split(".")[0] + "." + tok.rsplit(":", 1)[0]
            tok = book_chap.split(".")[0] + "." + tok
        elif book_chap:
            tok = book_chap + ":" + tok
        else:
            raise RefError(f"cannot parse {cell!r}")
        out.append(tok)
    return out


def _sections(path):
    with lzma.open(path, "rt", encoding="utf-8-sig") as f:
        lines = f.read().split("\n")
    exp = [i for i, l in enumerate(lines) if l.startswith("#DataStart(Expanded)")]
    end = [i for i, l in enumerate(lines) if l.startswith("#DataEnd(Expanded)")]
    if not exp or not end:
        raise SystemExit(f"{path}: TVTMS Expanded section not found")
    tbl = [i for i, l in enumerate(lines) if i > end[0] and l.startswith("English (NRSV")]
    if not tbl:
        raise SystemExit(f"{path}: TVTMS English/Hebrew table not found")
    simple = []
    for l in lines[tbl[0] + 2:]:
        if l.startswith("'==="):
            break
        c = l.split("\t")
        if len(c) > 1 and c[0].strip():
            simple.append((c[0], c[1]))
    expanded = [l.split("\t") for l in lines[exp[0] + 1:end[0]]]
    return simple, [c for c in expanded if len(c) > 4 and c[3].rstrip("*") in _ACTIONS and "Greek" in c[0]]


def load(conn, sources_dir):
    path = Path(sources_dir) / "stepbible" / "TVTMS.txt.xz"
    simple, greek = _sections(path)
    rows = {"hebrew": {}, "lxx": {}}
    skipped = dup = 0

    def add(scheme, src, can):
        nonlocal dup
        if src in rows[scheme]:
            dup += 1
        else:
            rows[scheme][src] = can

    for eng, heb in simple:
        try:
            can = _osis(eng)
            srcs = [_osis(t) for t in _split_cell(heb)]
        except (RefError, AttributeError):
            skipped += 1
            continue
        if not srcs:
            skipped += 1
        for s in srcs:
            add("hebrew", s, can)
    parsed = []
    for n, c in enumerate(greek):
        try:
            parsed.append((_rank(c[0]), n, _osis(c[1]), _osis(c[2])))
        except RefError:
            skipped += 1
    conflicts = 0
    for _, _, src, can in sorted(parsed):
        if src in rows["lxx"] and rows["lxx"][src] != can:
            conflicts += 1
        add("lxx", src, can)
    conn.executemany("INSERT INTO versification VALUES (?, ?, ?)",
                     [(s, a, b) for s, m in rows.items() for a, b in m.items()])
    print(f"versification: hebrew={len(rows['hebrew'])} lxx={len(rows['lxx'])} "
          f"skipped={skipped} duplicate-source-refs-dropped={dup} lxx-conflicts(differing target)={conflicts}")
    return sum(len(m) for m in rows.values())
