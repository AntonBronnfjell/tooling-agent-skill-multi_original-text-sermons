#!/usr/bin/env python3
"""Cross-check the SBL verses in data/bible.db against the published SBLGNT (Faithlife).

The SBL verse rows are built from MACULA Greek (scripts/loaders/macula.py) and re-keyed to KJV
verse numbers. Faithlife's plain-text SBLGNT (sources/sblgnt/<Book>.txt.xz, SBL numbering) is the
authority for the text. The two numberings differ in a few places (3John 14/15, Rev 12:18, Acts 19:40/41,
2Cor 13:12-14 ...), so the comparison is per chapter: both sides are flattened to one word stream
(Greek match_key: no punctuation, case, brackets or apparatus marks) and diffed. Equal streams are
fine even if a verse boundary moved; any other difference is reported against the verses it touches.
A chapter present on one side only is not compared (the Faithlife file lists which chapters exist).

    python3 scripts/check_sblgnt.py [--db FILE] [--sources DIR] [--ref Rom.16.25 ...] [--max N]

Exit 0 = no mismatch beyond punctuation/case; 1 = mismatches; 2 = DB or sources missing.
"""
import argparse
import lzma
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from otslib import db as otsdb  # noqa: E402
from otslib import norm  # noqa: E402

_LINE = re.compile(r"^(\w+) (\d+):(\d+)\t(.*)$")
# SBLGNT apparatus anchors (U+2E00-U+2E0F, optionally followed by a variant-unit digit: ⸀1ἄλλῳ),
# editorial brackets, and punctuation match_key does not know (em dash, parentheses, Greek ; and ·)
_MARKS = re.compile("[\u2e00-\u2e0f]\\d*|[\u27e6\u27e7\\[\\]\u2014()\u037e\u0387]")
# Faithlife numbering -> KJV numbering, the only places the two differ beyond a verse boundary that the
# chapter-level word stream already absorbs: Phil 1:16/17 are swapped, and Rev 12:18 is the first sentence of
# KJV Rev 13:1 (it crosses a chapter boundary). Everything else (3John 14/15, Acts 19:40/41, 2Cor 13:12-14 ...)
# stays inside one chapter and needs no mapping.
FL_TO_KJV = {("Phil", 1, 16): ("Phil", 1, 17), ("Phil", 1, 17): ("Phil", 1, 16), ("Rev", 12, 18): ("Rev", 13, 1)}
DEFAULT_STATUS = ("Rom.16.24", "Rom.16.25", "Rom.16.26", "Rom.16.27")


def _clean(s):
    return unicodedata.normalize("NFC", _MARKS.sub("", s)).strip()


def load_faithlife(directory):
    """-> {(book, chapter, verse): text} from every <Book>.txt[.xz] in `directory`."""
    out = {}
    for p in sorted(Path(directory).glob("*.txt*")):
        opener = lzma.open if p.suffix == ".xz" else open
        with opener(p, "rt", encoding="utf-8-sig") as f:
            for line in f:
                m = _LINE.match(line.rstrip("\n"))
                if m:
                    out[(m.group(1), int(m.group(2)), int(m.group(3)))] = _clean(m.group(4))
    return out


def _words(text):
    return norm.match_key(_clean(text), "grc").split()


def _stream(verses):
    """verses: [(ref, text)] in order -> (words, owner ref per word)."""
    words, owners = [], []
    for ref, text in verses:
        for w in _words(text):
            words.append(w)
            owners.append(ref)
    return words, owners


def _ref(b, c, v):
    return f"{b}.{c}.{v}"


def check(conn, sblgnt_dir, status_refs=DEFAULT_STATUS):
    raw = load_faithlife(sblgnt_dir)
    fl = {}
    for k in sorted(raw):  # KJV-keyed; a verse that gains text from another Faithlife verse is joined in file order
        t = FL_TO_KJV.get(k, k)
        fl[t] = (fl[t] + " " + raw[k]) if t in fl else raw[k]
    db = {}
    for ref, text in conn.execute("SELECT ref, text FROM verses WHERE corpus='grnt' AND witness='SBL'"):
        b, c, v = ref.split(".")
        db[(b, int(c), int(v))] = text
    fl_by, db_by = defaultdict(list), defaultdict(list)
    for k in sorted(fl):
        fl_by[k[:2]].append(k)
    for k in sorted(db):
        db_by[k[:2]].append(k)
    mismatches = []
    for ch in sorted(fl_by):
        fa, fo = _stream([(_ref(*k), fl[k]) for k in fl_by[ch]])
        da, do = _stream([(_ref(*k), db[k]) for k in db_by.get(ch, [])])
        if fa == da:
            continue
        touched = {}
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, fa, da, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            for ref in set(fo[i1:i2]) | set(do[j1:j2]):
                touched.setdefault(ref, (" ".join(fa[i1:i2]), " ".join(da[j1:j2])))
        # a DB verse with no words at all in this chapter's stream still counts (empty row)
        for k in db_by.get(ch, []):
            if k not in fl and not _words(db[k]):
                touched.setdefault(_ref(*k), ("", ""))
        for ref in sorted(touched, key=lambda r: tuple(int(x) if x.isdigit() else x for x in r.split("."))):
            b, c, v = ref.split(".")
            k = (b, int(c), int(v))
            mismatches.append({"ref": ref, "faithlife": fl.get(k), "db": db.get(k),
                               "diff_faithlife": touched[ref][0], "diff_db": touched[ref][1]})
    status = {}
    for r in status_refs:
        b, c, v = r.split(".")
        k = (b, int(c), int(v))
        status[r] = (k in fl, k in db)
    return {"chapters": len(fl_by), "faithlife_verses": len(fl), "db_verses": len(db),
            "mismatches": mismatches, "status": status}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db")
    ap.add_argument("--sources", help="sources/ directory (default: <repo>/sources)")
    ap.add_argument("--ref", action="append", help="also report presence of this ref (OSIS) in file and DB")
    ap.add_argument("--max", type=int, default=40, help="mismatches to print (default 40; 0 = all)")
    a = ap.parse_args(argv)
    sources = Path(a.sources) if a.sources else HERE.parent / "sources"
    sdir = sources / "sblgnt"
    dbp = Path(a.db) if a.db else otsdb.db_path()
    if not dbp.is_file() or not sdir.is_dir():
        print(f"ERROR: need DB ({dbp}) and {sdir}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    try:
        rep = check(conn, sdir, tuple(a.ref) if a.ref else DEFAULT_STATUS)
    finally:
        conn.close()
    print(f"SBLGNT (Faithlife) chapters {rep['chapters']}, verses {rep['faithlife_verses']}; "
          f"DB SBL verses {rep['db_verses']}")
    for r, (in_file, in_db) in rep["status"].items():
        print(f"  {r}: Faithlife file {'present' if in_file else 'absent'}; DB {'present' if in_db else 'absent'}")
    mm = rep["mismatches"]
    print(f"{len(mm)} verse(s) differ beyond punctuation/case")
    for m in mm if a.max == 0 else mm[:a.max]:
        print(f"MISMATCH {m['ref']}\n  faithlife: {m['faithlife']}\n  db:        {m['db']}\n"
              f"  differing words: faithlife [{m['diff_faithlife']}] vs db [{m['diff_db']}]")
    return 1 if mm else 0


if __name__ == "__main__":
    sys.exit(main())
