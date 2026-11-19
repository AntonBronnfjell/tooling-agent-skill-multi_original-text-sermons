"""Rahlfs LXX (CCAT/CATSS) -> words/verses, corpus `lxx`, refs in canonical English numbering.

Source files are headerless TSVs keyed by a global word id: text_accented (id, ccat id, word; a few
rows have only id, word), versification_original (first word id of each verse -> Rahlfs ref),
patched_623693 (CATSS morph), 09-lexemes (lemma), final_Strongs (G####, may be empty).
"""
import lzma
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
    ver = [(int(c[0]), c[1]) for c in _rows(d / "versification_original.csv.xz")]
    starts = [v[0] for v in ver]

    pos, canon = {}, {}
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
            canon[src] = canonical(conn, "lxx", src)
        ref = canon[src]
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
    print(f"lxx: {len(word_rows)} words, {len(vrows)} verses; skipped {skipped_words} words in "
          f"{len(skipped_books)} non-OSIS books ({', '.join(sorted(skipped_books)) or '-'})")
    return len(word_rows) + len(vrows)
