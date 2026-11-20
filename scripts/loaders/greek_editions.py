"""Ground-truth verse text for the TR and Byz witnesses, replacing the TAGNT reconstruction.

TAGNT lists every edition's words in NA order with displacement marks; some marks are inconsistent, so
the TR/Byz verse text rebuilt from them can come out scrambled (Mark 7:30, 2 Pet 1:18), and its spelling
is NA's. This loader replaces those `verses` rows with the printed editions; TAGNT `words` and
`variants` rows are left untouched.

- Byz: Robinson-Pierpont 2018 (byztxt/byzantine-majority-text, csv-unicode/ccat/no-variants).
- TR: Scrivener 1894. The accented text is eBible.org `grctr`; a verse is taken from it only when its
  words equal Robinson's unaccented Scrivener 1894 transcription (byztxt/greektext-scrivener), ignoring
  accents, case, movable nu and word division, with an appended subscription cut off. Elsewhere `grctr`
  follows another TR edition (Stephanus 1550: Matt 2:11 εὗρον, Rev 16:5 ὅσιος) and is not used.

Source verse numbers are mapped to KJV refs by aligning the words with the TAGNT text of the same
edition (the loaders/macula.py approach): Byz prints Rom 16:25-27 after 14:23 and swaps Matt 23:13/14,
and both editions divide some verses unlike the KJV (2 Cor 8:13/14, Heb 1:1/2).
A verse with no ground-truth text keeps its TAGNT text and gets an `order_flags` row; one in
otslib.editions.KNOWN_SCRAMBLED is marked `known scrambled`. Whole verses printed in another chapter get
an informational `placement differs: <W> prints after <c:v>` row (Byz Rom 16:25-27 after 14:23).
"""
import csv
import json
import lzma
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from loaders import macula
from otslib import norm
from otslib.editions import KJV_BREAK, KNOWN_SCRAMBLED, NO_GROUND_TRUTH, PLACEMENT
from otslib.editions import KNOWN_SCRAMBLED_REASON as SCRAMBLED

CORPUS = "grnt"
# eBible / Robinson file book codes -> OSIS
BOOKS = {
    "MAT": "Matt", "MT": "Matt", "MAR": "Mark", "MR": "Mark", "LUK": "Luke", "LU": "Luke",
    "JOH": "John", "ACT": "Acts", "AC": "Acts", "ROM": "Rom", "RO": "Rom", "1CO": "1Cor", "2CO": "2Cor",
    "GAL": "Gal", "GA": "Gal", "EPH": "Eph", "PHP": "Phil", "PHI": "Phil", "COL": "Col",
    "1TH": "1Thess", "2TH": "2Thess", "1TI": "1Tim", "2TI": "2Tim", "TIT": "Titus", "PHM": "Phlm",
    "HEB": "Heb", "JAM": "Jas", "JAS": "Jas", "1PE": "1Pet", "2PE": "2Pet", "1JO": "1John",
    "2JO": "2John", "3JO": "3John", "JUD": "Jude", "JUDE": "Jude", "REV": "Rev", "RE": "Rev",
}
# RP marks a dash with '-', eBible with '—': punctuation that no other witness carries
_DASH = re.compile(r"\s*[-‐-―]\s*")
_LATIN = str.maketrans("αβγδεζηθικλμνξοπρσςτυφχψω", "abgdezhyiklmnxoprsstufcqw")


def _clean(text):
    """Paragraph marks (¶) and dashes are layout; elision marks and other punctuation stay."""
    return re.sub(r"\s+", " ", _DASH.sub(" ", text.replace("¶", " "))).strip()


def _book(path):
    return BOOKS.get(path.name.split(".")[0])


# ---------------------------------------------------------------- sources

def read_byz(byz_dir):
    """RP CSVs (chapter,verse,text; one file per book) -> [(src_ref, text)], file order within a book."""
    out = []
    for path in sorted(Path(byz_dir).glob("*.csv.xz")):
        book = _book(path)
        if not book:
            continue
        with lzma.open(path, "rt", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                text = _clean(row["text"])
                if text:  # RP leaves Acts 24:7 empty
                    out.append((f"{book}.{int(row['chapter'])}.{int(row['verse'])}", text))
    return out


def read_vpl(path):
    """eBible VPL ('BOOK C:V text' per line) -> [(src_ref, text)]."""
    out = []
    with lzma.open(path, "rt", encoding="utf-8-sig") as f:
        for line in f:
            m = re.match(r"^(\w+) (\d+):(\d+) (.*)$", line.rstrip("\n"))
            if m and m.group(1) in BOOKS and m.group(4).strip():
                out.append((f"{BOOKS[m.group(1)]}.{m.group(2)}.{m.group(3)}", _clean(m.group(4))))
    return out


def read_robinson(rob_dir):
    """Robinson text-only files (lowercase beta code without accents, `c:v` verse markers, [TITLES])
    -> {src_ref: [words]}, final sigma written as s."""
    out = {}
    for path in sorted(Path(rob_dir).glob("*.xz")):
        book = _book(path)
        if not book:
            continue
        with lzma.open(path, "rt", encoding="latin-1") as f:
            text = re.sub(r"\[[^\]]*\]", " ", f.read())
        cur = None
        for tok in text.split():
            m = re.fullmatch(r"(\d+):(\d+)", tok)
            if m:
                cur = f"{book}.{int(m.group(1))}.{int(m.group(2))}"
                out.setdefault(cur, [])
            elif cur:
                out[cur].append(tok.replace("v", "s"))
    return out


# ---------------------------------------------------------------- word check (TR)

def _beta(word):
    """Accent-, case- and punctuation-free key in Robinson's Latin letters."""
    return re.sub(r"[^a-z]", "", norm.strip_accents(word).casefold().translate(_LATIN))


def _same_word(a, b):
    """Equal, or differing only by movable nu (ἐστί/ἐστίν, πᾶσι/πᾶσιν; not ἔχει/ἔχειν) or οὕτω(ς)."""
    if a == b:
        return True
    short, long_ = sorted((a, b), key=len)
    if long_ == short + "n":
        return len(short) >= 3 and short[-1] in "ei" and not long_.endswith("ein")
    return long_ == short + "s" and short in ("outw", "acri", "mecri")


def verify(words, reference):
    """words: display tokens of one verse; reference: Robinson's words for it. -> how many leading tokens
    of `words` equal `reference` (extra tokens at the end, an appended subscription, are cut), or None
    when they differ. Word division may differ (εἴκοσι τρεῖς / eikositreis)."""
    keys = [_beta(w) for w in words]
    cut = len(keys)
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, keys, reference, autojunk=False).get_opcodes():
        a, b = keys[i1:i2], reference[j1:j2]
        if tag == "equal":
            continue
        if tag == "delete" and i2 == len(keys) and j1 == len(reference):
            cut = i1
        elif tag == "replace" and len(a) == len(b) and all(_same_word(x, y) for x, y in zip(a, b)):
            continue
        elif not ("".join(a) and "".join(a) == "".join(b)):
            return None
    return cut or None


# ---------------------------------------------------------------- KJV refs

def _tokens(verses):
    return [(ref, t) for ref, text in verses for t in text.split()]


def assign_refs(src, tgt):
    """src: [(src_ref, token)] in source order; tgt: [(kjv_ref, token)] in KJV order (the TAGNT text of
    the same edition). -> [kjv_ref per src token]. Per book: macula._align, then a book-wide round for
    verses printed in another chapter (Byz Rom 16:25-27 after 14:23)."""
    by_book, t_by_book = defaultdict(list), defaultdict(list)
    for i, (ref, _) in enumerate(src):
        by_book[ref.split(".")[0]].append(i)
    for x in tgt:
        t_by_book[x[0].split(".")[0]].append(x)
    out = [None] * len(src)
    for book, idx in by_book.items():
        t = t_by_book.get(book, [])
        pair = {}
        if t:
            mk = [macula._wkey(src[i][1]) for i in idx]
            tk = [macula._wkey(x[1]) for x in t]
            pair = macula._align(mk, [src[i][0].split(".")[1] for i in idx], tk, [x[0].split(".")[1] for x in t])
            mu = [k for k in range(len(idx)) if k not in pair]
            used = set(pair.values())
            tu = [j for j in range(len(t)) if j not in used]
            for x, y in macula._blocks([mk[k] for k in mu], [tk[j] for j in tu], 4):
                pair[mu[x]] = tu[y]
            _repair_split_edges([src[i][0] for i in idx], mk, tk, [x[0] for x in t], pair)
        refs = macula.follow_neighbours([src[i][0] for i in idx],
                                        [t[pair[k]][0] if k in pair else None for k in range(len(idx))])
        for k, r in zip(idx, refs):
            out[k] = r
    return _keep_edges(src, out)


def _repair_split_edges(src_refs, m_keys, t_keys, t_refs, pair):
    """A source verse whose edge word aligned into a neighbouring KJV verse (Byz prints Matt 23:14 first:
    its opening Οὐαὶ matched KJV 23:13's Οὐαὶ while the rest matched 23:14): when the next aligned word
    of the same source verse sits in another KJV verse and an equal free word stands just before it,
    move the edge word there."""
    used = set(pair.values())
    aligned = sorted(pair)
    for a, b in reversed(list(zip(aligned, aligned[1:]))):
        if src_refs[a] != src_refs[b] or t_refs[pair[a]] == t_refs[pair[b]]:
            continue
        for j in range(pair[b] - 1, max(pair[b] - (b - a), 0) - 1, -1):
            if j not in used and t_keys[j] == m_keys[a] and t_refs[j] == t_refs[pair[b]]:
                used.discard(pair[a])
                pair[a] = j
                used.add(j)
                break


def _keep_edges(src, refs):
    """Accept a move to another KJV verse only for a whole source verse or a run of >= 2 words at its
    start or end (2 Cor 8:13 ἀλλ’ ἐξ ἰσότητος… -> 8:14; Matt 17:15 καὶ λέγων -> 17:14). A single moved
    word, or a run inside the verse, comes from TAGNT placing a reordered word by NA's verse (Mark 7:22
    κλοπαί) and stays in its printed verse."""
    out = list(refs)
    i = 0
    while i < len(src):
        e = i
        while e < len(src) and src[e][0] == src[i][0]:
            e += 1
        k = i
        while k < e:
            m = k
            while m < e and refs[m] == refs[k]:
                m += 1
            whole, edge = k == i and m == e, m - k >= 2 and (k == i or m == e)
            if refs[k] != src[k][0] and not (whole or edge):
                out[k:m] = [src[q][0] for q in range(k, m)]
            k = m
        i = e
    return out


# ---------------------------------------------------------------- load

def _bag_diff(a, b):
    ca, cb = Counter(a), Counter(b)
    return sum(((ca - cb) + (cb - ca)).values())


def rebuild(conn, witness, src, trusted):
    """src: [(src_ref, text)] in source order; trusted: src refs whose text is ground truth.
    Replaces the witness's `verses` rows and its `order_flags`. -> stats."""
    old = {r: t for r, t in conn.execute(
        "SELECT ref, text FROM verses WHERE corpus=? AND witness=?", (CORPUS, witness))}
    known = {r for (r,) in conn.execute("SELECT DISTINCT ref FROM verses WHERE corpus=?", (CORPUS,))}
    tgt = sorted(_tokens(old.items()), key=lambda x: macula._ref_key(x[0]))  # stable: verse order kept
    toks = _tokens(src)
    verses, good = defaultdict(list), defaultdict(lambda: True)
    split = defaultdict(set)  # source verse -> KJV verses its words went to
    for (sref, tok), kref in zip(toks, assign_refs(toks, tgt)):
        verses[kref].append(tok)
        good[kref] = good[kref] and sref in trusted
        split[sref].add(kref)
    # words moved across a verse break the edition prints elsewhere: both verses are affected. A source
    # verse that moves whole to one KJV verse (Rom 16:25-27 in Byz) is renumbering, not a boundary move.
    broken = {r for ks in split.values() if len(ks) > 1 for r in ks}
    placed = _placement(split, [s for s, _ in src], witness)
    stats = {"same": 0, "reordered": 0, "different_words": 0, "added": 0, "flagged": 0,
             "unplaced": sorted(r for r in verses if r not in known), "examples": []}
    rows, flags = [], []
    for ref in sorted((set(verses) & known) | set(old), key=macula._ref_key):
        if ref in verses and good[ref]:
            text = norm.display(" ".join(verses[ref]), "grc")
            _count(stats, ref, old.get(ref), text)
        elif ref in old:
            text = old[ref]
            flags.append((CORPUS, witness, ref, NO_GROUND_TRUTH))
        else:
            continue  # unverified text at a ref TAGNT does not give this edition: leave it out
        rows.append((CORPUS, witness, ref, text, norm.match_key(text, "grc")))
    flags += [(CORPUS, witness, r, KJV_BREAK) for r in sorted(broken & {x[2] for x in rows}, key=macula._ref_key)]
    flags = [(c, w, r, SCRAMBLED if r in KNOWN_SCRAMBLED.get(witness, ()) else why) for c, w, r, why in flags]
    flags += [(CORPUS, witness, r, why) for r, why in placed.items() if r in {x[2] for x in rows}]
    flags = list(dict.fromkeys(flags))
    stats["flagged"] = sum(1 for f in flags if f[3] in (NO_GROUND_TRUTH, SCRAMBLED))
    stats["kjv_breaks"] = sum(1 for f in flags if f[3] == KJV_BREAK)
    stats["placement"] = len(placed)
    stats["scrambled"] = sum(1 for f in flags if f[3] == SCRAMBLED)
    conn.execute("DELETE FROM verses WHERE corpus=? AND witness=?", (CORPUS, witness))
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", rows)
    conn.execute("DELETE FROM order_flags WHERE corpus=? AND witness=?", (CORPUS, witness))
    conn.executemany("INSERT INTO order_flags VALUES (?,?,?,?)", flags)
    return stats


def _placement(split, src_refs, witness):
    """{kjv_ref: reason} for source verses that move whole to a KJV verse in another chapter and are not
    printed next to their KJV neighbour (Byz Rom 16:25-27 after 14:23; a verse renumbered across a chapter
    break, like Rev 12:18 -> 13:1, stays adjacent and is not listed). The reason names the source verse
    they are printed after."""
    one = {s: next(iter(ks)) for s, ks in split.items() if len(ks) == 1}
    kjv = sorted({k for ks in split.values() for k in ks if k}, key=macula._ref_key)
    at = {k: i for i, k in enumerate(kjv)}
    out, last, run = {}, None, None
    for sref in dict.fromkeys(src_refs):
        k = one.get(sref)
        if not (k and k.split(".")[:2] != sref.split(".")[:2]):
            last, run = sref, None
            continue
        if run is None:  # first verse of a moved run: away from where its KJV predecessor is printed?
            prev = one.get(last) if last else None
            run = bool(prev) and at[k] != at.get(prev, -2) + 1
        if run:
            out[k] = f"{PLACEMENT}: {witness} prints after {':'.join(last.split('.')[1:])}"
    return out


def _count(stats, ref, old, new):
    if old is None:
        stats["added"] += 1
        return
    a, b = [macula._wkey(w) for w in old.split()], [macula._wkey(w) for w in new.split()]
    if a == b:
        stats["same"] += 1
    elif sorted(a) == sorted(b):
        stats["reordered"] += 1
    else:
        stats["different_words"] += 1
        n = _bag_diff(a, b)
        if n >= 3:
            stats["examples"].append((n, ref, old, new))


def load_byz(conn, sources_dir):
    src = read_byz(Path(sources_dir) / "byz")
    return rebuild(conn, "Byz", src, {r for r, _ in src})


def load_tr(conn, sources_dir):
    tr = Path(sources_dir) / "tr"
    vpl = tr / "grctr_vpl.txt.xz"
    src = read_vpl(vpl) if vpl.is_file() else []
    scr = read_robinson(tr / "scrivener")
    kept, trusted, rejected = [], set(), []
    for ref, text in src:
        words = text.split()
        cut = verify(words, scr[ref]) if ref in scr else None
        if cut is None:
            rejected.append(ref)
            kept.append((ref, text))  # still aligned (keeps neighbours right), never used as text
        else:
            kept.append((ref, " ".join(words[:cut])))
            trusted.add(ref)
    stats = rebuild(conn, "TR", kept, trusted)
    stats["rejected"] = rejected
    return stats


def _pins(sources_dir):
    """{'tr': ..., 'byz': ...} from MANIFEST.json, for the meta rows."""
    out = {}
    try:
        entries = json.loads((Path(sources_dir) / "MANIFEST.json").read_text(encoding="utf-8"))["entries"]
    except (OSError, ValueError, KeyError):
        return out
    for e in entries:
        top = e.get("path", "").split("/")[0]
        if top in ("tr", "byz") and e.get("status") == "vendored":
            out.setdefault(top, set()).add(e.get("commit_or_version", ""))
    return {k: ", ".join(sorted(v)) for k, v in out.items()}


def load(conn, sources_dir, out=print):
    pins = _pins(sources_dir)
    byz, tr = load_byz(conn, sources_dir), load_tr(conn, sources_dir)
    conn.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("byz_source", "Robinson-Pierpont 2018 Byzantine Textform (byztxt/byzantine-majority-text "
                       f"{pins.get('byz', 'unpinned')}); verses without it keep TAGNT text, see order_flags"),
        ("tr_source", "Scrivener 1894: eBible.org grctr accented text, used only where it equals Robinson's "
                      f"Scrivener 1894 word for word ({pins.get('tr', 'unpinned')}); "
                      f"{len(tr['rejected'])} grctr verses differ and keep TAGNT text, see order_flags")])
    n = 0
    for wit, s in (("Byz", byz), ("TR", tr)):
        out(f"greek_editions {wit}: same_as_tagnt={s['same']} reordered={s['reordered']} "
            f"different_words={s['different_words']} (>=3 words: {len(s['examples'])}) added={s['added']} "
            f"flagged_no_ground_truth_or_scrambled={s['flagged']} (known_scrambled={s['scrambled']}) "
            f"kjv_verse_breaks={s['kjv_breaks']} placement_differs={s['placement']} unplaced={len(s['unplaced'])}"
            + (f" grctr_not_scrivener={len(s['rejected'])}" if "rejected" in s else ""))
        n += s["same"] + s["reordered"] + s["different_words"] + s["added"]
    return n
