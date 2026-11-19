#!/usr/bin/env python3
"""Real-data check of LXX -> English versification.

Compares the Greek Strongs of each canonical LXX (Rahlfs) verse in data/bible.db with the `greekstrong`
column of MACULA Hebrew for the same canonical ref (MT numbering folded to KJV through the `hebrew`
scheme). A ref is flagged when a neighbouring ref in the same book (+-60 verses) matches the LXX verse
at least 0.25 better than the ref itself, i.e. the text probably landed in the wrong verse.
Genuine LXX/MT divergence (different text, e.g. Jeremiah, Job, Proverbs) also scores low but is only
flagged when a neighbour fits clearly better.

    python3 scripts/check_lxx_alignment.py [--db FILE] [--list] [--min-chapter-flags N]
"""
import argparse
import lzma
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from otslib import db as otsdb  # noqa: E402
from loaders.macula import USFM  # noqa: E402

STOP = {"2532", "3588", "846", "1722", "1519", "3754", "3756", "1161", "1063", "2443", "3361", "1537", "575",
        "4314", "1909", "3778", "1473", "4771", "1510", "5613"}


def _key(r):
    b, c, v = r.split(".")
    return b, int(c), int(v)


def macula_strongs(conn, sources):
    heb = dict(conn.execute("SELECT source_ref, canonical_ref FROM versification WHERE scheme='hebrew'"))
    mac = defaultdict(set)
    with lzma.open(sources / "macula" / "macula-hebrew.tsv.xz", "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            c = line.rstrip("\n").split("\t")
            m = re.match(r"(\w+) (\d+):(\d+)!", c[1])
            if not m or len(c) < 11 or not c[10] or m.group(1) not in USFM:
                continue
            can = heb.get(f"{USFM[m.group(1)]}.{int(m.group(2))}.{int(m.group(3))}",
                          f"{USFM[m.group(1)]}.{int(m.group(2))}.{int(m.group(3))}")
            for g in c[10].split():
                g = g.lstrip("G").lstrip("0")
                if g and g not in STOP:
                    mac[can].add(g)
    return mac


def lxx_strongs(conn):
    lxx = defaultdict(set)
    for ref, s in conn.execute("SELECT ref, strongs FROM words WHERE corpus='lxx' AND witness='Rahlfs' AND strongs<>''"):
        g = re.sub(r"[A-Za-z]$", "", s.lstrip("G").lstrip("0"))
        if g not in STOP:
            lxx[ref].add(g)
    return lxx


def score(a, b):
    return len(a & b) / len(b) if a and b else None


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else None


def ref_sets(conn):
    """-> (KJV OT ref set = Hebrew WLC verse refs, LXX Rahlfs-family verse refs)."""
    kjv = {r for (r,) in conn.execute("SELECT ref FROM verses WHERE corpus='hebot' AND witness='WLC'")}
    lxx = {r for (r,) in conn.execute("SELECT DISTINCT ref FROM verses WHERE corpus='lxx'")}
    return kjv, lxx


def coverage(conn):
    """(a) LXX refs outside the KJV ref space; (b) KJV refs with Hebrew text but no Rahlfs text."""
    kjv, lxx = ref_sets(conn)
    main = {r for (r,) in conn.execute("SELECT ref FROM verses WHERE corpus='lxx' AND witness='Rahlfs'")}
    return sorted(lxx - kjv, key=_key), sorted(kjv - main, key=_key)


def check(conn, sources):
    mac, lxx = macula_strongs(conn, sources), lxx_strongs(conn)
    refs = sorted(set(lxx) & set(mac), key=_key)
    order = sorted(mac, key=_key)
    idx = {r: i for i, r in enumerate(order)}
    flagged, low, jflag, jlow = [], 0, [], 0
    for r in refs:
        if len(mac[r]) < 4:
            continue
        s = score(lxx[r], mac[r])
        if s < 0.4:
            low += 1
        best, bestr = s, r
        for o in order[max(0, idx[r] - 60): idx[r] + 61]:
            if o.split(".")[0] != r.split(".")[0] or len(mac[o]) < 4:
                continue
            t = score(lxx[r], mac[o])
            if t is not None and t > best + 0.25:
                best, bestr = t, o
        if bestr != r:
            flagged.append((r, round(s, 2), bestr, round(best, 2)))
        js = jaccard(lxx[r], mac[r])
        if js < 0.2:
            jlow += 1
        jb, jr = js, r
        for o in order[max(0, idx[r] - 60): idx[r] + 61]:
            if o.split(".")[0] != r.split(".")[0] or len(mac[o]) < 4:
                continue
            t = jaccard(lxx[r], mac[o])
            if t is not None and t > jb + 0.15:
                jb, jr = t, o
        if jr != r:
            jflag.append((r, round(js, 2), jr, round(jb, 2)))
    return len(refs), low, flagged, jlow, jflag


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--sources", type=Path, default=HERE.parent / "sources")
    ap.add_argument("--list", action="store_true", help="list every flagged ref")
    ap.add_argument("--min-chapter-flags", type=int, default=3, help="chapters with at least N flagged refs are summarised")
    a = ap.parse_args(argv)
    conn = sqlite3.connect(f"file:{a.db or otsdb.db_path()}?mode=ro", uri=True)
    n, low, flagged, jlow, jflag = check(conn, a.sources)
    print(f"refs compared: {n}; low overlap (<0.4): {low}; flagged (neighbour fits >=0.25 better): {len(flagged)}")
    print(f"symmetric (Jaccard): <0.2: {jlow}; flagged (neighbour >=0.15 better): {len(jflag)}")
    outside, empty = coverage(conn)
    print(f"(a) LXX refs outside the KJV OT ref space: {len(outside)}")
    print(f"(b) KJV refs with Hebrew text but no Rahlfs text: {len(empty)}")
    if a.list:
        print("  (a)", ", ".join(outside))
        print("  (b)", ", ".join(empty))
        for f in jflag:
            print("  J", *f)
    else:
        bb = defaultdict(int)
        for r in empty:
            bb[r.split(".")[0]] += 1
        print("  (b) by book:", dict(sorted(bb.items(), key=lambda x: -x[1])[:25]))
        print("  (a) first:", ", ".join(outside[:15]))
    by = defaultdict(list)
    for f in flagged:
        by[".".join(f[0].split(".")[:2])].append(f)
    for ch, lst in sorted(by.items(), key=lambda x: -len(x[1])):
        if a.list:
            for f in lst:
                print("  ", *f)
        elif len(lst) >= a.min_chapter_flags:
            print(f"  {ch}: {len(lst)} flagged, e.g. {lst[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
