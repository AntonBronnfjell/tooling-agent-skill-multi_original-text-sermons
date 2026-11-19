"""MACULA enrichment: Louw-Nida/SDBH domains and syntax roles on existing words rows,
plus authoritative SBL verse text (MACULA Greek *is* the SBLGNT)."""
import lzma
import re
from collections import defaultdict
from pathlib import Path

from otslib import norm
from otslib.refs import canonical

USFM = {
    "GEN": "Gen", "EXO": "Exod", "LEV": "Lev", "NUM": "Num", "DEU": "Deut", "JOS": "Josh",
    "JDG": "Judg", "RUT": "Ruth", "1SA": "1Sam", "2SA": "2Sam", "1KI": "1Kgs", "2KI": "2Kgs",
    "1CH": "1Chr", "2CH": "2Chr", "EZR": "Ezra", "NEH": "Neh", "EST": "Esth", "JOB": "Job",
    "PSA": "Ps", "PRO": "Prov", "ECC": "Eccl", "SNG": "Song", "ISA": "Isa", "JER": "Jer",
    "LAM": "Lam", "EZK": "Ezek", "DAN": "Dan", "HOS": "Hos", "JOL": "Joel", "AMO": "Amos",
    "OBA": "Obad", "JON": "Jonah", "MIC": "Mic", "NAM": "Nah", "HAB": "Hab", "ZEP": "Zeph",
    "HAG": "Hag", "ZEC": "Zech", "MAL": "Mal", "MAT": "Matt", "MRK": "Mark", "LUK": "Luke",
    "JHN": "John", "ACT": "Acts", "ROM": "Rom", "1CO": "1Cor", "2CO": "2Cor", "GAL": "Gal",
    "EPH": "Eph", "PHP": "Phil", "COL": "Col", "1TH": "1Thess", "2TH": "2Thess", "1TI": "1Tim",
    "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm", "HEB": "Heb", "JAS": "Jas", "1PE": "1Pet",
    "2PE": "2Pet", "1JN": "1John", "2JN": "2John", "3JN": "3John", "JUD": "Jude", "REV": "Rev",
}
_REF = re.compile(r"^(\w{3}) (\d+):(\d+)!(\d+)$")
_BRACKETS = re.compile(r"[\[\]⟦⟧]")


def clean(s):
    """Drop SBLGNT editorial brackets ([[ ]], [ ]) so they never reach verse text."""
    return _BRACKETS.sub("", s)


def _token(text, after):
    """`after` is ' ' or bare punctuation (',' '.' '·' ';' '’'), never carrying its own space;
    SBLGNT prints a space after every token, elision included (δι’ οὗ)."""
    return clean(text) + clean(after).strip() + " "


def _wkey(surface):
    """Surface key for alignment: no accents, punctuation, elision marks or case."""
    return re.sub(r"\W+", "", norm.strip_accents(surface or "")).casefold()


# MACULA's SBLGNT versification differs from KJV (which every other witness here, TAGNT included, uses)
# in dozens of places: verses missing/extra (2Cor 13:13, Acts 19:41, 3John 15, Rev 12:18), boundaries
# moved mid-sentence (Gal 2:19/20, Rom 9:11/12 ...) and even swapped verses (Phil 1:16/17). Rather than
# keeping a hand list, every MACULA word takes the KJV ref of the TAGNT SBL word it aligns with.

def _blocks(a, b, min_len):
    from difflib import SequenceMatcher
    for i, j, n in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        if n >= min_len:
            for k in range(n):
                yield i + k, j + k


def _align(m_keys, m_chap, t_keys, t_chap):
    """-> {m_index: t_index}. Round 1 aligns the whole book monotonically; later rounds re-align the
    leftovers chapter by chapter (blocks >= 3 words) to recover moved/swapped verses."""
    pair = dict(_blocks(m_keys, t_keys, 2))
    for _ in range(4):
        mu, tu = defaultdict(list), defaultdict(list)
        used_t = set(pair.values())
        for i, c in enumerate(m_chap):
            if i not in pair:
                mu[c].append(i)
        for j, c in enumerate(t_chap):
            if j not in used_t:
                tu[c].append(j)
        new = {}
        for c, mi in mu.items():
            tj = tu.get(c)
            if not tj:
                continue
            for x, y in _blocks([m_keys[i] for i in mi], [t_keys[j] for j in tj], 3):
                new[mi[x]] = tj[y]
        if not new:
            break
        pair.update(new)
    _repair_edges(m_keys, t_keys, pair)
    # Gap fill: runs of unaligned words between two aligned neighbours are matched against the
    # unaligned TAGNT words between the same neighbours, on 3-letter stems (ἀλλά ~ ἀλλ᾽).
    pair.update(_fill_gaps(m_keys, t_keys, pair))
    return pair


def _repair_edges(m_keys, t_keys, pair):
    """Round 1 can glue one word onto the wrong side of a moved/swapped verse (Phil 1:16/17: the
    'οἱ' opening the love-clause aligns with the 'οἱ' opening the ambition-clause). At a jump, if the
    word just before the successor's TAGNT position is free and equal, move the pair there; then
    let every aligned word pull equal unaligned neighbours in on both sides."""
    used = set(pair.values())
    for m in sorted(pair):
        j, nxt = pair[m], pair.get(m + 1)
        if nxt is not None and nxt != j + 1 and nxt - 1 not in used and m_keys[m] == t_keys[nxt - 1]:
            used.discard(j)
            pair[m] = nxt - 1
            used.add(nxt - 1)
    for step in (-1, 1):
        for m in sorted(pair, reverse=step == 1):
            while True:
                m2, j2 = m + step, pair[m] + step
                if (m2 < 0 or m2 >= len(m_keys) or j2 < 0 or j2 >= len(t_keys) or m2 in pair
                        or j2 in used or m_keys[m2] != t_keys[j2]):
                    break
                pair[m2] = j2
                used.add(j2)
                m = m2


def _fill_gaps(m_keys, t_keys, pair):
    new = {}
    anchors = sorted(pair.items())
    # only gaps flanked by real anchors on both sides (no book-start/end sentinels)
    for (ma, ta), (mb, tb) in zip(anchors, anchors[1:]):
        if mb - ma > 1 and tb - ta > 1:
            ms = [k[:3] for k in m_keys[ma + 1:mb]]
            ts = [k[:3] for k in t_keys[ta + 1:tb]]
            for x, y in _blocks(ms, ts, 1):
                new[ma + 1 + x] = ta + 1 + y
    return new


def _assign_refs(conn, words):
    """words: [(src_ref, n, ...)] sorted by source order. -> [target ref per word], using TAGNT SBL refs."""
    by_book = defaultdict(list)
    for i, w in enumerate(words):
        by_book[w[0].split(".")[0]].append(i)
    tagnt = defaultdict(list)
    for ref, pos, surf, ed in conn.execute(
            "SELECT ref, pos, surface, editions FROM words WHERE corpus='grnt' AND witness='TAGNT'"):
        if _sbl_token(ed):
            tagnt[ref.split(".")[0]].append((_ref_key(ref), pos, ref, surf))
    out = [None] * len(words)
    for book, idx in by_book.items():
        t = sorted(tagnt.get(book, []))
        pair = _align([_wkey(words[i][2]) for i in idx], [words[i][0].split(".")[1] for i in idx],
                      [_wkey(x[3]) for x in t], [x[2].split(".")[1] for x in t]) if t else {}
        tgt = [t[pair[k]][2] if k in pair else None for k in range(len(idx))]
        # unaligned words (SBL-only readings, Mark 16, John 7:53-8:11) follow the nearest aligned
        # word of the same source verse; a verse with none keeps its own ref.
        k = 0
        while k < len(idx):
            e = k
            while e < len(idx) and words[idx[e]][0] == words[idx[k]][0]:
                e += 1
            last = None
            for q in range(k, e):
                if tgt[q]:
                    last = tgt[q]
                elif last:
                    tgt[q] = last
            nxt = None
            for q in range(e - 1, k - 1, -1):
                if tgt[q]:
                    nxt = tgt[q]
                elif nxt:
                    tgt[q] = nxt
            for q in range(k, e):
                out[idx[q]] = tgt[q] or words[idx[q]][0]
            k = e
    return out


def _rows(path):
    with lzma.open(path, "rt", encoding="utf-8-sig") as f:
        header = f.readline().rstrip("\n").split("\t")
        idx = {n: i for i, n in enumerate(header)}
        for line in f:
            cells = line.rstrip("\n").split("\t")
            m = _REF.match(cells[idx["ref"]])
            if not m or m.group(1) not in USFM:
                continue
            get = lambda name: cells[idx[name]] if idx[name] < len(cells) else ""
            yield f"{USFM[m.group(1)]}.{m.group(2)}.{m.group(3)}", int(m.group(4)), get


def _sbl_token(editions):
    return "SBL" in (re.sub(r"[»«]\d+", "", t) for t in (editions or "").split("+"))


def _ref_key(ref):
    book, c, v = ref.split(".")
    return (book, int(c), int(v))


def _lkey(lemma):
    # TAHOT sometimes lists alternate lemma forms ("אֶבְיָסָף, אֲבִיאָסָף"); the first is the headword.
    return norm.strip_accents((lemma or "").split(",")[0].strip()).casefold()


def _skey(strongs):
    m = re.search(r"\d+", strongs or "")
    return str(int(m.group())) if m else ""


def _enrich(conn, corpus, witness, by_verse, only_sbl=False):
    """by_verse: canonical ref -> [(lemma, strong, domain, role)] in source order.
    Pass 1 joins on (ref, strip_accents(lemma), nth occurrence of the lemma in the verse).
    Pass 2 gives rows still unmatched a second chance on (ref, Strong's number, nth occurrence), which
    covers lemma-form differences between STEPBible and MACULA. Returns (matched, total).
    TAGNT stores one row per word (witness 'TAGNT'); a word is SBL's iff its editions carry the SBL token."""
    rows = [(r, ref, lem, st) for r, ref, lem, st, ed in conn.execute(
        "SELECT rowid, ref, lemma, strongs, editions FROM words WHERE corpus=? AND witness=? ORDER BY ref, pos",
        (corpus, witness)) if not only_sbl or _sbl_token(ed)]
    by_lemma, by_strong = {}, {}
    for ref, items in by_verse.items():
        nl, ns = defaultdict(int), defaultdict(int)
        for lemma, strong, dom, role in items:
            kl, ks = _lkey(lemma), _skey(strong)
            nl[kl] += 1
            by_lemma[(ref, kl, nl[kl])] = (dom, role)
            if ks:
                ns[ks] += 1
                by_strong[(ref, ks, ns[ks])] = (dom, role)
    seen_l, seen_s = defaultdict(int), defaultdict(int)
    updates = []
    for rowid, ref, lemma, strongs in rows:
        kl, ks = _lkey(lemma), _skey(strongs)
        seen_l[(ref, kl)] += 1
        hit = by_lemma.get((ref, kl, seen_l[(ref, kl)]))
        if ks:
            seen_s[(ref, ks)] += 1
            if not (hit and (hit[0] or hit[1])):
                hit = by_strong.get((ref, ks, seen_s[(ref, ks)]))
        if hit and (hit[0] or hit[1]):
            updates.append((hit[0], hit[1], rowid))
    conn.executemany("UPDATE words SET domain=?, syntax_role=? WHERE rowid=?", updates)
    return len(updates), len(rows)


def _lemma_check(conn, by_verse):
    """Count SBL verses whose MACULA lemma set differs from the TAGNT SBL words at the same ref."""
    t = defaultdict(set)
    for ref, lem, ed in conn.execute("SELECT ref, lemma, editions FROM words WHERE corpus='grnt' AND witness='TAGNT'"):
        if _sbl_token(ed):
            t[ref].add(_lkey(lem))
    bad = 0
    checked = 0
    for ref, items in by_verse.items():
        if ref not in t:
            continue
        checked += 1
        m = {_lkey(x[0]) for x in items}
        if len(m ^ t[ref]) > 0.25 * max(len(m), len(t[ref])):  # tolerate lemma-form/variant noise
            bad += 1
    return bad, checked


def load_greek(conn, sources_dir):
    path = Path(sources_dir) / "macula" / "macula-greek-SBLGNT.tsv.xz"
    if not path.is_file():
        path = Path(sources_dir) / "macula-greek-SBLGNT.tsv.xz"
    words = []  # (src_ref, n, text, after, lemma, ln, role, strong)
    for ref, n, get in _rows(path):
        words.append((ref, n, get("text"), get("after"), get("lemma"), get("ln"),
                      get("role") or get("class"), get("strong")))
    words.sort(key=lambda w: (_ref_key(w[0]), w[1]))
    verses = defaultdict(list)
    for tgt, w in zip(_assign_refs(conn, [(w[0], w[1], w[2]) for w in words]), words):
        verses[tgt].append(w)
    old = {r: t for r, t in conn.execute(
        "SELECT ref, text FROM verses WHERE corpus='grnt' AND witness='SBL'")}
    new_rows, by_verse = [], {}
    stats = {"replaced_same": 0, "replaced_different": 0, "added": 0, "examples": []}
    for ref, ws in verses.items():
        text = norm.display(re.sub(r"\s+", " ", "".join(_token(w[2], w[3]) for w in ws)).strip(), "grc")
        new_rows.append(("grnt", "SBL", ref, text, norm.match_key(text, "grc")))
        by_verse[ref] = [(w[4], w[7], w[5], w[6]) for w in ws]
        if ref not in old:
            stats["added"] += 1
        elif old[ref] == text:
            stats["replaced_same"] += 1
        else:
            stats["replaced_different"] += 1
            if len(stats["examples"]) < 6:
                stats["examples"].append((ref, old[ref], text))
    stats["old_not_in_macula"] = sorted(set(old) - set(verses))
    conn.execute("DELETE FROM verses WHERE corpus='grnt' AND witness='SBL'")
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", new_rows)
    stats["matched"], stats["total"] = _enrich(conn, "grnt", "TAGNT", by_verse, only_sbl=True)
    stats["lemma_mismatch"], stats["lemma_checked"] = _lemma_check(conn, by_verse)
    return stats


def load_hebrew(conn, sources_dir):
    path = Path(sources_dir) / "macula" / "macula-hebrew.tsv.xz"
    if not path.is_file():
        path = Path(sources_dir) / "macula-hebrew.tsv.xz"
    verses = defaultdict(list)
    cache = {}
    for ref, n, get in _rows(path):
        if ref not in cache:
            cache[ref] = canonical(conn, "hebrew", ref)
        verses[cache[ref]].append(
            (n, get("lemma"), get("strongnumberx"), get("sdbh") or get("lexdomain"),
             get("class") or get("pos")))
    by_verse = {}
    for ref, ws in verses.items():
        # file order is already source order (prefix rows precede their word); do not re-sort,
        # or words of verses merged by versification would interleave
        by_verse.setdefault(ref, []).extend(w[1:] for w in ws)
    matched, total = _enrich(conn, "hebot", "WLC", by_verse)
    return {"matched": matched, "total": total}


def load(conn, sources_dir, out=print):
    g = load_greek(conn, sources_dir)
    h = load_hebrew(conn, sources_dir)
    for name, s in (("grnt", g), ("hebot", h)):
        rate = 100.0 * s["matched"] / s["total"] if s["total"] else 0.0
        out(f"macula {name}: enriched {s['matched']}/{s['total']} words ({rate:.1f}%)")
    out(f"macula SBL verses: replaced_different={g['replaced_different']} "
        f"replaced_same={g['replaced_same']} added={g['added']} "
        f"existing_not_in_macula={len(g['old_not_in_macula'])}")
    out(f"macula SBL verses with lemma-set mismatch vs TAGNT SBL words: "
        f"{g['lemma_mismatch']}/{g['lemma_checked']}")
    return g["matched"] + h["matched"] + g["replaced_different"] + g["added"]
