#!/usr/bin/env python3
"""Cross-check the SBL verses in data/bible.db against the published SBLGNT (Faithlife).

The SBL verse rows are built from MACULA Greek (scripts/loaders/macula.py) and re-keyed to KJV
verse numbers. Faithlife's plain-text SBLGNT (sources/sblgnt/<Book>.txt.xz, SBL numbering) is the
authority for the text. The two numberings differ in a few places (3John 14/15, Rev 12:18, Acts 19:40/41,
2Cor 13:12-14 ...), so SHIFTS records the exact known offset per chapter; the Faithlife stream is re-cut with it and compared
verse by verse, so any other difference (including a word moved across a boundary) is caught. Words are Greek match_key (no
punctuation, case, brackets or apparatus marks). A chapter present in the DB but not in Faithlife is
reported (and its verses count as mismatches).

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
# Faithlife numbering -> KJV numbering for whole verses: Phil 1:16/17 are swapped, and Rev 12:18 is the first
# sentence of KJV Rev 13:1 (it crosses a chapter boundary). Words shifted across a verse boundary inside one
# chapter (3John 14/15, Acts 19:40/41, 2Cor 13:12-14 ...) are pinned in SHIFTS below.
FL_TO_KJV = {("Phil", 1, 16): ("Phil", 1, 17), ("Phil", 1, 17): ("Phil", 1, 16), ("Rev", 12, 18): ("Rev", 13, 1)}
# Known verse-boundary differences between Faithlife (SBL numbering) and the KJV-keyed DB, one entry per chapter:
# {verse: n} means that at the boundary after that verse, Faithlife's running word count minus the DB's is n
# (n > 0: the last n words of the Faithlife verse sit at the start of the next DB verse; n < 0: the first |n|
# words of the next Faithlife verse sit at the end of this DB verse). Derived once by auditing the real data
# (every listed chapter has an identical chapter word stream); the check re-cuts the Faithlife stream with
# these offsets and compares verse by verse, so any other difference, including a different word moved across
# one of these boundaries, is flagged. Phil 1 and Rev 12/13 are handled by FL_TO_KJV. Add an entry only after
# confirming the shift is a versification difference, not a text change.
SHIFTS = {
    ("1John", 2): {13: -7}, ("1Pet", 3): {15: -5}, ("1Thess", 1): {2: 1}, ("1Thess", 2): {6: -7, 11: -6},
    ("2Cor", 8): {13: 3}, ("2Cor", 10): {4: 2}, ("2Cor", 13): {12: 5, 13: 20}, ("3John", 1): {14: -11},
    ("Acts", 2): {10: -4}, ("Acts", 3): {19: -9}, ("Acts", 4): {5: 2}, ("Acts", 5): {39: 3}, ("Acts", 9): {28: 6},
    ("Acts", 13): {38: 10}, ("Acts", 19): {40: 6}, ("Acts", 24): {18: -6}, ("Col", 1): {21: -3},
    ("Eph", 2): {14: 6}, ("Eph", 5): {13: -6}, ("Gal", 2): {19: 2}, ("Heb", 3): {9: -2}, ("Heb", 7): {20: 8},
    ("Heb", 12): {22: 1}, ("Luke", 1): {73: 3}, ("Luke", 6): {17: -10}, ("Luke", 7): {18: 9}, ("Mark", 3): {19: -4},
    ("Mark", 12): {14: 4}, ("Matt", 17): {14: -2}, ("Matt", 20): {4: -3}, ("Phil", 2): {7: 5}, ("Rev", 2): {27: -7},
    ("Rev", 17): {9: 4}, ("Rom", 1): {9: -5}, ("Rom", 3): {25: -5}, ("Rom", 7): {9: -3}, ("Rom", 9): {11: -7}}
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


def check(conn, sblgnt_dir, status_refs=DEFAULT_STATUS, shifts=SHIFTS):
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

    def add(ref, diff_f, diff_d):
        b, c, v = ref.split(".")
        k = (b, int(c), int(v))
        mismatches.append({"ref": ref, "faithlife": fl.get(k), "db": db.get(k),
                           "diff_faithlife": diff_f, "diff_db": diff_d})

    def diff(fa, da, fo, do):
        touched = {}
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, fa, da, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            for ref in set(fo[i1:i2]) | set(do[j1:j2]):
                touched.setdefault(ref, (" ".join(fa[i1:i2]), " ".join(da[j1:j2])))
        return touched

    for ch in sorted(set(fl_by) | set(db_by)):
        touched = {}
        shift = shifts.get(ch, {})
        verses = sorted(set(fl_by.get(ch, [])) | set(db_by.get(ch, [])))
        fa, _ = _stream([(_ref(*k), fl[k]) for k in fl_by.get(ch, [])])
        pos = fcum = 0
        for n, k in enumerate(verses):
            ref = _ref(*k)
            fcum += len(_words(fl[k])) if k in fl else 0
            end = len(fa) if n == len(verses) - 1 else fcum - shift.get(k[2], 0)
            exp = fa[pos:end]  # the Faithlife words that belong to this verse under the known shift
            pos = max(pos, end)
            da = _words(db[k]) if k in db else []
            if exp != da:
                touched[ref] = diff(exp, da, [ref] * len(exp), [ref] * len(da)).get(ref, ("", ""))
        for ref in sorted(touched, key=lambda r: tuple(int(x) if x.isdigit() else x for x in r.split("."))):
            add(ref, *touched[ref])
    status = {}
    for r in status_refs:
        b, c, v = r.split(".")
        k = (b, int(c), int(v))
        status[r] = (k in fl, k in db)
    return {"chapters": len(fl_by), "faithlife_verses": len(fl), "db_verses": len(db),
            "mismatches": mismatches, "status": status,
            "db_only_chapters": [f"{b}.{c}" for b, c in sorted(set(db_by) - set(fl_by))]}


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
    if rep["db_only_chapters"]:
        print(f"DB chapters absent from Faithlife ({len(rep['db_only_chapters'])}): {', '.join(rep['db_only_chapters'])}")
    mm = rep["mismatches"]
    print(f"{len(mm)} verse(s) differ beyond punctuation/case")
    for m in mm if a.max == 0 else mm[:a.max]:
        print(f"MISMATCH {m['ref']}\n  faithlife: {m['faithlife']}\n  db:        {m['db']}\n"
              f"  differing words: faithlife [{m['diff_faithlife']}] vs db [{m['diff_db']}]")
    return 1 if mm else 0


if __name__ == "__main__":
    sys.exit(main())
