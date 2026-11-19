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


# MACULA SBLGNT numbers some NT verses the NRSV way; TAGNT (and every other witness here) uses KJV.
# (macula ref) -> [(first_n_words_to, target ref), ...]; None = take all remaining words.
# Verified against the TAGNT-derived refs: these are the only places where the verse set differs.
_KJV_REMAP = {
    "2Cor.13.12": [(5, "2Cor.13.12"), (None, "2Cor.13.13")],  # ἀσπάσασθε...φιλήματι | ἀσπάζονται...
    "2Cor.13.13": [(None, "2Cor.13.14")],
    "Acts.19.40": [(-6, "Acts.19.40"), (None, "Acts.19.41")],  # last 6 words = καὶ ταῦτα...ἐκκλησίαν
    "3John.1.15": [(None, "3John.1.14")],
    "Rev.12.18": [(None, "Rev.13.1")],
}


def _kjv_split(ref, ws):
    """-> [(target_ref, words)] with `ws` sorted by !n."""
    plan = _KJV_REMAP.get(ref)
    if not plan:
        return [(ref, ws)]
    out, start = [], 0
    for end, target in plan:
        stop = len(ws) if end is None else (len(ws) + end if end < 0 else end)
        out.append((target, ws[start:stop]))
        start = stop
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


def load_greek(conn, sources_dir):
    path = Path(sources_dir) / "macula" / "macula-greek-SBLGNT.tsv.xz"
    if not path.is_file():
        path = Path(sources_dir) / "macula-greek-SBLGNT.tsv.xz"
    verses = defaultdict(list)  # ref -> [(n, text, after, lemma, ln, role)]
    for ref, n, get in _rows(path):
        verses[ref].append((n, get("text"), get("after"), get("lemma"), get("ln"),
                            get("role") or get("class"), get("strong")))
    raw = verses
    verses = defaultdict(list)
    for ref in sorted(raw, key=_ref_key):  # source order, so merged verses read in order
        ws = sorted(raw[ref])
        for target, part in _kjv_split(ref, ws):
            verses[target].extend(part)
    old = {r: t for r, t in conn.execute(
        "SELECT ref, text FROM verses WHERE corpus='grnt' AND witness='SBL'")}
    new_rows, by_verse = [], {}
    stats = {"replaced_same": 0, "replaced_different": 0, "added": 0, "examples": []}
    for ref, ws in verses.items():
        text = norm.display(re.sub(r"\s+", " ", "".join(_token(t, a) for _, t, a, *_ in ws)).strip(), "grc")
        new_rows.append(("grnt", "SBL", ref, text, norm.match_key(text, "grc")))
        by_verse[ref] = [(w[3], w[6], w[4], w[5]) for w in ws]
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
    return g["matched"] + h["matched"] + g["replaced_different"] + g["added"]
