"""Rahlfs LXX (CCAT/CATSS) -> words/verses, corpus `lxx`, refs in canonical English numbering.

Versification: Rahlfs numbering is mapped to English (KJV/NRSV) with the Unbound exceptions-only map
`unbound_lxx_mapping_to_NRSV.csv` (vendored from the same upstream commit); a ref with no row keeps
its Rahlfs numbering (it already equals KJV). Rahlfs lettered sub-verses (`Esth.1.1a`) are folded into
their base canonical verse, appended in source order. TVTMS `lxx` rows are used ONLY for Psalms (they keep titles as verse 0, where Unbound folds
them into v.1); elsewhere they do not follow Rahlfs numbering (see scripts/check_lxx_alignment.py).

Source files are headerless TSVs keyed by a global word id: text_accented (id, ccat id, word; a few
rows have only id, word), versification_original (first word id of each verse -> Rahlfs ref),
patched_623693 (CATSS morph), 09-lexemes (lemma), final_Strongs (G####, may be empty).
"""
import lzma
import re
from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path

from otslib import norm
from otslib.refs import BOOKS, canonical

# LXX book id -> (OSIS book, witness). Double texts: Joshua/Judges B (Vaticanus) is the main
# Rahlfs text and A is RahlfsA; Daniel OG is the main text and Theodotion is RahlfsTh.
_SPECIAL = {
    "Qoh": ("Eccl", "Rahlfs"), "Cant": ("Song", "Rahlfs"),
    "JoshB": ("Josh", "Rahlfs"), "JoshA": ("Josh", "RahlfsA"),
    "JudgB": ("Judg", "Rahlfs"), "JudgA": ("Judg", "RahlfsA"),
    "DanOG": ("Dan", "Rahlfs"), "DanTh": ("Dan", "RahlfsTh"),
}


_UNBOUND = {  # Unbound OT book index -> OSIS (15O = 2 Esdras: Ezra 1-10, Neh = ch 11-23, handled in _unbound)
    1: "Gen", 2: "Exod", 3: "Lev", 4: "Num", 5: "Deut", 6: "Josh", 7: "Judg", 8: "Ruth", 9: "1Sam", 10: "2Sam",
    11: "1Kgs", 12: "2Kgs", 13: "1Chr", 14: "2Chr", 15: "Ezra", 16: "Neh", 17: "Esth", 18: "Job", 19: "Ps",
    20: "Prov", 21: "Eccl", 22: "Song", 23: "Isa", 24: "Jer", 25: "Lam", 26: "Ezek", 27: "Dan", 28: "Hos",
    29: "Joel", 30: "Amos", 31: "Obad", 32: "Jonah", 33: "Mic", 34: "Nah", 35: "Hab", 36: "Zeph", 37: "Hag",
    38: "Zech", 39: "Mal"}
# Books where, absent an Unbound row, Rahlfs follows Hebrew numbering rather than KJV (Isa 63:19b/64:1-12;
# found with scripts/check_lxx_alignment.py: identity left Isa 64 shifted by one verse).
_HEBREW_NUMBERED = {"Isa"}
_SRC = re.compile(r"^(\w+)\.(\d+)\.(\d+)([a-z]*)(?:[-/]\d+)?$")  # `Jer.7.27/28`, `DanOG.5.26-28`: first verse of the range
last_stats = {}


def _unbound(path):
    """-> (targets, skip). targets: {(osis book, chapter, verse, letter): [KJV refs in file order]};
    skip: keys whose Unbound target is an A-book (deuterocanonical addition: Prayer of Azariah, Ps 151, Esther Additions...)."""
    out, skip = {}, set()
    with lzma.open(path, "rt", encoding="utf-8-sig") as f:
        for line in f:
            c = line.rstrip("\r\n").split("\t")
            if len(c) < 8 or c[0].startswith("#") or c[7] == "1" or not c[4] or not c[5]:
                continue
            if not c[3].endswith("O"):  # source book without an OSIS id
                continue
            ob = int(c[3][:-1])
            book = "Neh" if ob == 15 and int(c[4]) >= 11 else _UNBOUND[ob]
            key = (book, int(c[4]), int(c[5]), c[6])
            if not c[0].endswith("O"):
                skip.add(key)
                continue
            out.setdefault(key, []).append(f"{_UNBOUND[int(c[0][:-1])]}.{c[1]}.{c[2]}")
    return out, skip


# Explicit corrections, keyed by (osis book, chapter, verse, letter) AFTER the Prov chapter shift; value = KJV ref.
# Each was found with scripts/check_lxx_alignment.py / strongs comparison against MACULA Hebrew.
_OVERRIDES = {
    ("Jer", 36, 14, ""): "Jer.29.14",  # Unbound maps 36:14 to itself; TVTMS and the Strongs overlap say MT 29:14
    ("Jer", 25, 14, ""): "Jer.25.13",  # superscription "which Jeremiah prophesied against the nations" (MT 25:13b)
    ("Jer", 25, 20, ""): "Jer.49.34",  # Elam heading (placed last in Rahlfs 25:14-20)
    ("Jer", 38, 35, ""): "Jer.31.37",  # Rahlfs 38:35-37 = MT 31:37, 35, 36
    ("Jer", 38, 36, ""): "Jer.31.35",
    ("Jer", 38, 37, ""): "Jer.31.36",
    ("Deut", 23, 25, ""): "Deut.23.25",  # Rahlfs 23:25-26 = MT 23:25, 24
    ("Deut", 23, 26, ""): "Deut.23.24",
}
# CATSS numbers Prov 25-29 as chapters 32-36 (lettered 32.10a == Unbound 25:10a); 24, 30, 31 agree with Unbound.
_PROV_SHIFT = (32, 36, 7)


def target(conn, umap, skip, b, c, v, letter):
    """Rahlfs/CATSS source verse -> KJV ref, or None for deuterocanonical additions (skipped)."""
    if b == "Prov" and _PROV_SHIFT[0] <= c <= _PROV_SHIFT[1]:
        c -= _PROV_SHIFT[2]
    key = (b, c, v, letter)
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    own = f"{b}.{c}.{v}"
    ts = umap.get(key) or (letter and umap.get((b, c, v, "")))
    if not ts and (key in skip or (letter and (b, c, v, "") in skip)):
        return None
    if b == "Ps":  # Unbound folds Psalm titles into v.1; TVTMS keeps them as verse 0 (repo convention)
        return canonical(conn, "lxx", own)
    if ts:
        # one source verse feeding several KJV verses: its own ref, else the target with its verse number, else the first
        return own if own in ts else next((t for t in ts if t.rsplit(".", 1)[1] == str(v)), ts[0])
    return canonical(conn, "hebrew", own) if b in _HEBREW_NUMBERED else own


def _rows(path):
    with lzma.open(path, "rt", encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line:
                yield line.split("\t")


def _map(path):
    return {int(c[0]): c[-1] for c in _rows(path)}


def load(conn, sources_dir):
    d = Path(sources_dir) / "lxx"
    morph = _map(d / "patched_623693.csv.xz")
    lemma = _map(d / "09-lexemes.csv.xz")
    strongs = {i: s for i, s in _map(d / "final_Strongs.csv.xz").items() if s.startswith("G")}
    umap, skip = _unbound(d / "unbound_lxx_mapping_to_NRSV.csv.xz")
    ver = [(int(c[0]), c[1]) for c in _rows(d / "versification_original.csv.xz")]
    starts = [v[0] for v in ver]

    pos, canon, sources = {}, {}, {}
    lettered = 0
    skipped_additions, skipped_addition_verses = 0, set()
    verses = OrderedDict()
    word_rows = []
    skipped_words = 0
    skipped_books = set()
    for cols in _rows(d / "text_accented.csv.xz"):  # 3 columns, or 2 for the few inserted words
        wid, word = int(cols[0]), cols[-1]
        k = bisect_right(starts, wid) - 1
        if k < 0:
            skipped_words += 1
            continue
        book, ch, vs = ver[k][1].split(".")
        osis, witness = _SPECIAL.get(book, (book, "Rahlfs"))
        if osis not in BOOKS:  # deuterocanon, Odes, Psalms of Solomon, Bel/Sus ...
            skipped_words += 1
            skipped_books.add(book)
            continue
        src = f"{osis}.{ch}.{vs}"
        if src not in canon:
            m = _SRC.match(src)
            b, c_, v_, letter = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
            canon[src] = target(conn, umap, skip, b, c_, v_, letter)
            if letter and canon[src]:
                lettered += 1
        ref = canon[src]
        if ref is None:  # deuterocanonical addition (Unbound A-book target)
            skipped_additions += 1
            skipped_addition_verses.add(src)
            continue
        sources.setdefault((witness, ref), set()).add(re.sub(r"[a-z]+$", "", src))
        surface = norm.display(word, "grc")
        key = (witness, ref)
        pos[key] = pos.get(key, 0) + 1
        word_rows.append(("lxx", witness, ref, pos[key], surface, norm.nfc(lemma.get(wid, "")),
                          strongs.get(wid, ""), morph.get(wid, ""), "", "", "", ""))
        verses.setdefault(key, []).append(surface)
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", word_rows)
    vrows = []
    for (witness, ref), ws in verses.items():
        text = " ".join(ws)
        vrows.append(("lxx", witness, ref, text, norm.match_key(text, "grc")))
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", vrows)
    collisions = sorted((w, r, sorted(ss)) for (w, r), ss in sources.items() if len(ss) > 1)
    last_stats.update(lettered_source_verses_folded=lettered, skipped_addition_words=skipped_additions,
                      skipped_addition_verses=sorted(skipped_addition_verses), collisions=collisions, skipped_books=sorted(skipped_books))
    print(f"lxx: {len(collisions)} canonical refs receive >=2 distinct source verses; "
          f"{lettered} lettered source verses folded into their base verse; skipped {skipped_additions} words "
          f"({len(skipped_addition_verses)} source verses) whose Unbound target is a deuterocanonical addition")
    print(f"lxx: {len(word_rows)} words, {len(vrows)} verses; skipped {skipped_words} words in "
          f"{len(skipped_books)} non-OSIS books ({', '.join(sorted(skipped_books)) or '-'})")
    return len(word_rows) + len(vrows)
