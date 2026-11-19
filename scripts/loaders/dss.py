"""Biblical Dead Sea Scrolls (ETCBC/dss Text-Fabric) -> words/verses, corpus `dss`.

A sermon quote must contain only what the manuscript actually reads, so text is rebuilt from SIGN
nodes, never from the word `glyph` (which silently includes reconstructed and removed letters):
  verse text   joins words by the `after` feature (space behind the word; absent = proclitic bound to the
               next word, so scroll `מעמל`/`וישבע` is not split as `מ עמל`/`ו ישבע`); keeps `cons`/`numr` signs; drops signs with rec (reconstructed), rem (removed),
               alt (alternative reading) or vac (vacat); drops punct/missing/empty/term/unc-marker signs;
               morpheme break U+05F3 joins, maqaf stays, non-breaking space is a space.
               Signs flagged unc (uncertain but physically present) and cor (correction) are kept.
  words.surface  the word's letters with reconstructed ones bracketed `או[ר]`, removed ones omitted.
  words.editions comma-separated flags present in the word: rec, unc, cor, rem, alt, vac.
Witness = scroll siglum (scroll node containing the word's first slot) with punctuation/spaces
removed and the book letter following `<n>Q` capitalised: 1Qisaa -> 1QIsaa, 4Qisad -> 4QIsad.
Words whose `book` is not a biblical-book acronym (manuscript names such as 4Q56, Mur88) are skipped.
"""
import re
from bisect import bisect_right
from collections import OrderedDict
from pathlib import Path

from otslib import norm, tf
from otslib.refs import BOOKS, canonical

_ACRONYM = {"Ex": "Exod", "Is": "Isa"}  # every other DSS acronym equals the OSIS id
_FLAGS = ("rec", "unc", "cor", "rem", "alt", "vac")
_SIGLUM_CASE = re.compile(r"^(\d+Q)([a-z])")


def siglum(raw):
    s = re.sub(r"[^0-9A-Za-z]", "", raw)
    return _SIGLUM_CASE.sub(lambda m: m.group(1) + m.group(2).upper(), s)


def _render(slots, f):
    """-> (surface with [rec] brackets, verse-text piece, flags) for one word's signs."""
    chars = []  # (char, is_reconstructed)
    flags = set()
    for s in slots:
        typ = f["type"].get(s)
        for name in _FLAGS:
            if s in f[name]:
                flags.add(name)
        if typ in ("cons", "numr"):
            if s in f["rem"] or s in f["alt"] or s in f["vac"]:
                continue
            chars.append((f["glyph"].get(s, ""), s in f["rec"]))
        elif typ == "sep":
            g = f["glyph"].get(s, "")
            if g == "׳":
                continue
            chars.append((" " if g.isspace() else g, s in f["rec"]))
    surface, k = [], 0
    while k < len(chars):
        if chars[k][1]:
            j = k
            while j < len(chars) and chars[j][1]:
                j += 1
            surface.append("[" + "".join(c for c, _ in chars[k:j]) + "]")
            k = j
        else:
            surface.append(chars[k][0])
            k += 1
    text = "".join(c for c, rec in chars if not rec)
    return "".join(surface), text, ",".join(n for n in _FLAGS if n in flags)


def load(conn, sources_dir):
    d = Path(sources_dir) / "dss"

    def feat(n):
        return tf.read_feature(d / f"{n}.tf.xz")

    book = feat("book")
    chapter, verse, lex, scroll_name = feat("chapter"), feat("verse"), feat("lex"), feat("scroll")
    after = feat("after")
    otype_ranges = []
    for line in tf._lines(d / "otype.tf.xz"):
        spec, _, name = line.partition("\t")
        a, _, b = spec.partition("-")
        otype_ranges.append((int(a), int(b or a), name))
    scrolls = {n for a, b, name in otype_ranges if name == "scroll" for n in range(a, b + 1)}
    words = {n for n, b in book.items() if _ACRONYM.get(b, b) in BOOKS and chapter.get(n, "").isdigit()
             and verse.get(n, "").isdigit()}
    skipped_book = sorted({b for b in book.values() if _ACRONYM.get(b, b) not in BOOKS})
    skipped_book_words = sum(1 for b in book.values() if _ACRONYM.get(b, b) not in BOOKS)
    skipped_ref = sum(1 for n, b in book.items() if _ACRONYM.get(b, b) in BOOKS and n not in words)

    oslots = tf.read_oslots(d / "oslots.tf.xz", nodes=words | scrolls)
    runs = []  # (first slot, last slot, siglum) of every scroll
    for n in scrolls:
        sl = oslots.get(n)
        if not sl or n not in scroll_name:
            continue
        sig = siglum(scroll_name[n])
        a = prev = sl[0]
        for s in sl[1:]:
            if s != prev + 1:
                runs.append((a, prev, sig))
                a = s
            prev = s
        runs.append((a, prev, sig))
    runs.sort()
    starts = [r[0] for r in runs]

    f = {n: feat(n) for n in ("type", "glyph", "rec", "rem", "alt", "vac", "unc", "cor")}
    pos = {}
    verses = OrderedDict()
    word_rows = []
    skipped_scroll = 0
    for w in sorted(words):
        slots = oslots.get(w)
        if not slots:
            skipped_scroll += 1
            continue
        k = bisect_right(starts, slots[0]) - 1
        if k < 0 or runs[k][1] < slots[0]:
            skipped_scroll += 1
            continue
        witness = runs[k][2]
        surface, text, flags = _render(slots, f)
        if not surface.strip():
            continue
        osis = _ACRONYM.get(book[w], book[w])
        ref = canonical(conn, "hebrew", f"{osis}.{int(chapter[w])}.{int(verse[w])}")
        key = (witness, ref)
        pos[key] = pos.get(key, 0) + 1
        word_rows.append(("dss", witness, ref, pos[key], norm.nfc(surface), norm.nfc(re.sub(r"_\w+$", "", lex.get(w, ""))),
                          "", "", "", flags, "", ""))
        v = verses.setdefault(key, {"text": "", "gap": False})
        piece = text.strip()
        if piece:
            if v["gap"] and v["text"]:
                v["text"] += " "
            v["text"] += piece
            v["gap"] = w in after
        elif w in after:  # a lost word still separates its neighbours
            v["gap"] = True
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", word_rows)
    vrows = []
    for (witness, ref), v in verses.items():
        text = norm.display(v["text"], "heb")
        if not text:
            continue
        vrows.append(("dss", witness, ref, text, norm.match_key(text, "heb")))
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", vrows)
    print(f"dss: {len(word_rows)} words, {len(vrows)} verses, {len({r[1] for r in vrows})} witnesses; skipped "
          f"{skipped_book_words} words with non-book `book` ({len(skipped_book)} values), {skipped_ref} biblical words "
          f"without numeric chapter/verse, {skipped_scroll} words without a scroll")
    return len(word_rows) + len(vrows)
