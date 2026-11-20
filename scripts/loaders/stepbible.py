"""STEPBible loader: TAHOT (Hebrew OT), TAGNT (Greek NT), TBESH/TBESG (lexicons).

Columns are mapped by header name, never by index. Canonical refs are English/KJV
versification in OSIS form. Hebrew text is the Qere (STEPBible's main text).
"""
import lzma
import re
from collections import OrderedDict
from pathlib import Path

from otslib import editions as ed
from otslib import norm
from otslib.refs import RefError, parse_ref

# witness name in the DB -> token in the TAGNT `editions` column
GREEK_WITNESSES = OrderedDict([("SBL", "SBL"), ("NA", "NA28"), ("THGNT", "Tyn"),
                               ("WH", "WH"), ("Byz", "Byz"), ("TR", "TR")])

_ROW = re.compile(r"^([0-9A-Za-z]{3})\.(\d+)\.(\d+)(?:\[(\d+)\.(\d+)\])?[^#]*#(\d+)=(\S*)$")
_HEADERS = {"eng (heb) ref & type", "word & type"}
_TRAIL_PUNCT = re.compile(r"[,.;·:?!;·]+$")
_DISPLACE = re.compile(r"(?:[»«][\d.]+)+$")
_SPELL = re.compile(r"\s*\+?([^:;]+):\s*([^;]*?)\s*;")
_book_cache = {}


def _open(path):
    return lzma.open(path, "rt", encoding="utf-8-sig")


def _book(abbr):
    if abbr not in _book_cache:
        try:
            _book_cache[abbr] = parse_ref(abbr + " 1").book
        except RefError:
            raise RuntimeError(f"STEPBible book abbreviation {abbr!r} missing from refs.py aliases")
    return _book_cache[abbr]


def _norm_name(s):
    return re.sub(r"\s+", " ", s.strip()).lower()


def _word_rows(path):
    """Yield (regex match of the ref cell, cells, name->index map) for each word row."""
    cols = None
    with _open(path) as f:
        for line in f:
            cells = line.rstrip("\n").split("\t")
            first = cells[0].strip()
            if _norm_name(first) in _HEADERS:
                cols = {_norm_name(c): i for i, c in enumerate(cells) if c.strip()}
                continue
            m = _ROW.match(first)
            if m and cols:
                yield m, cells, cols


def _cell(cells, cols, name):
    i = cols.get(name)
    return cells[i].strip() if i is not None and i < len(cells) else ""


def _canon_ref(m, use_kjv_alt):
    book = _book(m.group(1))
    if use_kjv_alt and m.group(4):
        return f"{book}.{m.group(4)}.{m.group(5)}"
    return f"{book}.{m.group(2)}.{m.group(3)}"


def _verse_row(corpus, witness, ref, text, lang):
    t = norm.display(text, lang)
    return (corpus, witness, ref, t, norm.match_key(t, lang))


# ---------------------------------------------------------------- Hebrew

def _heb(s):
    s = re.sub(r"\\ \\[ספ]\s*$", "", s)  # setumah/petuhah paragraph marker, not text
    s = s.replace("//", " ").replace("/", "").replace("\\", "")
    return norm.nfc(re.sub(r"\s+", " ", s).strip())


def _join_heb(surfaces):
    out = ""
    for s in surfaces:
        out += s if not out or out.endswith("־") else " " + s
    return out


def _ketiv(mean, spell):
    """Ketiv Hebrew for a Qere row, or None if it cannot be read reliably."""
    m = re.match(r"^K= [^()]*\(([^()]+)\)", mean)
    if not m:
        m = re.search(r";K= (\S.*?)\s*$", spell) if not mean else None
    return _heb(m.group(1)) if m else None


def _load_tahot(conn, sources_dir):
    verses = OrderedDict()  # ref -> list of (type, surface, ketiv-or-None, is_qere)
    word_rows = []
    pos = {}
    files = sorted((sources_dir / "stepbible").glob("TAHOT_*.txt.xz"))
    for path in files:
        for m, cells, cols in _word_rows(path):
            ref = _canon_ref(m, use_kjv_alt=False)
            typ = m.group(7)
            surf = _heb(_cell(cells, cols, "hebrew"))
            pos[ref] = pos.get(ref, 0) + 1
            tags = _cell(cells, cols, "expanded strong tags")
            lm = re.search(r"\{[HA]\w+=([^=}]+)=", tags)
            word_rows.append(("hebot", "WLC", ref, pos[ref], surf, norm.nfc(lm.group(1)) if lm else "",
                              re.sub(r"_[A-Za-z]+$", "", _cell(cells, cols, "root dstrong+instance")), _cell(cells, cols, "grammar"),
                              _cell(cells, cols, "translation"), typ, "", ""))
            ketiv = None
            if typ.startswith("Q"):
                ketiv = _ketiv(_cell(cells, cols, "meaning variants"), _cell(cells, cols, "spelling variants"))
            verses.setdefault(ref, []).append((typ, surf, ketiv, typ.startswith("Q")))
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", word_rows)
    vrows = []
    for ref, ws in verses.items():
        # X (reconstructed from LXX) and R (restored) are not in the Leningrad codex.
        wlc = [s for t, s, _, _ in ws if t not in ("X", "R") and s]
        if wlc:
            vrows.append(_verse_row("hebot", "WLC", ref, _join_heb(wlc), "heb"))
        qeres = [w for w in ws if w[3] and w[0] not in ("X", "R")]
        if qeres and all(w[2] for w in qeres):  # skip the verse if any Ketiv is unreadable
            ket = [(w[2] if w[3] else w[1]) for w in ws if w[0] not in ("X", "R") and (w[1] or w[2])]
            vrows.append(_verse_row("hebot", "Ketiv", ref, _join_heb(ket), "heb"))
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", vrows)
    return len(word_rows) + len(vrows)


# ---------------------------------------------------------------- Greek

def _tokens(editions):
    return [_DISPLACE.sub("", t) for t in editions.split("+") if t]


def _greek_surface(raw):
    s = re.sub(r"\s+\([^()]*\)$", "", raw.strip())
    return norm.nfc(s.replace("¶", "").strip())


def _substitutions(mean, spell):
    """-> list of (reading, [edition tokens], raw editions string) from the variant columns."""
    out = []
    for seg in mean.split(" ¦ "):
        sm = re.match(r"^(.*?) \([A-Za-z]*=", seg.strip())
        im = re.search(r" in: (\S+)\s*$", seg)
        if sm and im:
            out.append((norm.nfc(sm.group(1).strip()), _tokens(im.group(1)), im.group(1)))
    # ponytail: spelling variants are only applied when they parse as `EDS: word ;` groups
    # (every real row does); anything else is ignored.
    for eds, word in _SPELL.findall(spell):
        if word:
            out.append((norm.nfc(word), _tokens(eds.strip()), eds.strip()))
    return out


def _load_tagnt(conn, sources_dir):
    verses = OrderedDict()  # ref -> {witness: [surfaces]}
    word_rows, variant_rows = [], []
    pos = {}
    all_tokens = set(GREEK_WITNESSES.values())
    partial, dia = {}, set()  # ref -> rows not printed by every edition; refs holding διαπαντός
    for path in sorted((sources_dir / "stepbible").glob("TAGNT_*.txt.xz")):
        for m, cells, cols in _word_rows(path):
            ref = _canon_ref(m, use_kjv_alt=True)
            pos[ref] = pos.get(ref, 0) + 1
            p = pos[ref]
            surf = _greek_surface(_cell(cells, cols, "greek"))
            editions = _cell(cells, cols, "editions")
            present = set(_tokens(editions))
            subs = _substitutions(_cell(cells, cols, "meaning variants"), _cell(cells, cols, "spelling variants"))
            sub_by_token, row_disp, sub_disp = {}, ed.displacements(editions), {}
            for reading, toks, raw in subs:
                variant_rows.append((ref, p, reading, raw))
                for t in toks:
                    sub_by_token[t] = reading
                sub_disp.update(ed.displacements(raw))
            sg = [pair.split("=", 1) for pair in _cell(cells, cols, "dstrongs = grammar").split(" + ")]
            strongs = "+".join(x[0].strip() for x in sg)
            morph = " + ".join(x[1].strip() if len(x) > 1 else "" for x in sg)
            dic = _cell(cells, cols, "dictionary form = gloss")
            lemma = dic.split("=", 1)[0].split(",")[0].strip()
            word_rows.append(("grnt", "TAGNT", ref, p, surf, norm.nfc(lemma), strongs, morph,
                              _cell(cells, cols, "english translation"), editions, "", ""))
            if not all_tokens <= present:
                variant_rows.append((ref, p, surf, editions))
                partial.setdefault(ref, set()).add(p - 1)
            if re.search(r"δια\s?παντ", norm.strip_accents(surf).casefold()):
                dia.add(ref)
            # ponytail: main-word trailing punctuation is re-attached to substitutions lacking it.
            tail = _TRAIL_PUNCT.search(surf)
            for wit, tok in GREEK_WITNESSES.items():
                if tok in sub_by_token:
                    s = sub_by_token[tok]
                    if tail and not _TRAIL_PUNCT.search(s):
                        s += tail.group(0)
                elif tok in present:
                    s = surf
                else:
                    continue
                verses.setdefault(ref, {}).setdefault(wit, []).append(
                    (p - 1, ed.effective(tok, row_disp, sub_disp), s))
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", word_rows)
    conn.executemany("INSERT INTO variants VALUES (?,?,?,?)", variant_rows)
    vrows, reordered, other_verse, flags = [], {}, {}, []
    for ref, by_w in verses.items():
        for wit, ws in by_w.items():
            surfaces = [s for _, _, s in ws]
            if any(d == ed.OTHER_VERSE for _, d, _ in ws):
                other_verse[wit] = other_verse.get(wit, 0) + 1
            moved = ed.moved(ws)
            if moved:
                surfaces = _reorder_with_punct(ws)
                reordered[wit] = reordered.get(wit, 0) + 1
            # SBL text is replaced wholesale by MACULA's (loaders/macula.py), so it is never flagged; TR and
            # Byz flags are replaced by loaders/greek_editions.py
            if wit != "SBL" and ref in ed.KNOWN_SCRAMBLED.get(wit, ()):
                flags.append(("grnt", wit, ref, ed.KNOWN_SCRAMBLED_REASON))
            elif wit != "SBL" and moved:
                at_risk = ref in dia or _span_has_partial(ws, partial.get(ref, ()))
                flags.append(("grnt", wit, ref, ed.ORDER_UNCERTAIN if at_risk else ed.REBUILT))
            if surfaces:
                vrows.append(_verse_row("grnt", wit, ref, " ".join(surfaces), "grc"))
    conn.executemany("INSERT INTO verses VALUES (?,?,?,?,?)", vrows)
    conn.executemany("INSERT INTO order_flags VALUES (?,?,?,?)", flags)
    fmt = lambda d: ", ".join(f"{w}={n}" for w, n in d.items()) or "none"
    conn.executemany("INSERT INTO meta VALUES (?, ?)", [
        # TR/Byz/SBL verse text is replaced later (greek_editions, macula): only THGNT/WH/NA keep this order
        ("tagnt_reordered_verses_thgnt_wh_na", fmt({w: n for w, n in reordered.items() if w in ("THGNT", "WH", "NA")})),
        ("tagnt_other_verse_displacement_kept_in_place", fmt(other_verse))])
    return len(word_rows) + len(variant_rows) + len(vrows)


def _span_has_partial(entries, partial):
    """True if a moved word, or a row it jumps over, is not printed by every edition (its position among
    the other editions' rows is then a guess).
    # ponytail: the text is still reordered (the displacement marks are the only source); the flag is the
    # ceiling. Not reordering inside such spans would need NA's order to be better than the marks, unproven."""
    for row, d, _ in entries:
        if isinstance(d, int) and d:
            lo, hi = sorted((row, row + d))
            if any(lo <= r <= hi for r in partial):
                return True
    return False


def _reorder_with_punct(entries):
    """Reorder one edition's words (entries as for editions.order); trailing punctuation stays with its
    slot (a clause or verse end), not with the moved word."""
    punct, bare = [], []
    for _, _, s in entries:
        m = _TRAIL_PUNCT.search(s)
        punct.append(m.group(0) if m else "")
        bare.append(s[:m.start()] if m else s)
    return [bare[i] + p for i, p in zip(ed.order(entries), punct)]


# ---------------------------------------------------------------- lexicons

def _load_lexicon(conn, path, lang):
    rows, cols = [], None
    with _open(path) as f:
        for line in f:
            cells = line.rstrip("\n").split("\t")
            if cells[0].strip().lower().startswith("estrong") and len(cells) > 4:
                cols = {_norm_name(c): i for i, c in enumerate(cells)}
                continue
            if not cols or not re.match(r"^[HG]\d{4}", cells[0]):
                continue
            get = lambda name: cells[cols[name]].strip() if cols.get(name, 99) < len(cells) else ""
            strongs = re.split(r"\s=", get("dstrong"))[0].strip() or cells[0].strip()
            gloss_i = cols["gloss"]
            definition = cells[gloss_i + 1].strip() if gloss_i + 1 < len(cells) else ""
            rows.append((strongs, norm.nfc(get("hebrew" if lang == "heb" else "greek")), lang,
                         get("gloss"), definition))
    conn.executemany("INSERT INTO lexicon VALUES (?,?,?,?,?)", rows)
    return len(rows)


def load(conn, sources_dir):
    sources_dir = Path(sources_dir)
    n = _load_tahot(conn, sources_dir) + _load_tagnt(conn, sources_dir)
    n += _load_lexicon(conn, sources_dir / "stepbible" / "TBESH.txt.xz", "heb")
    n += _load_lexicon(conn, sources_dir / "stepbible" / "TBESG.txt.xz", "grc")
    return n
