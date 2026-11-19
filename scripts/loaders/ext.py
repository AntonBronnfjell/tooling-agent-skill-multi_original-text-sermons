"""Extra-biblical 1st-century Greek usage evidence, corpus `ext` (word usage only, never doctrine).

Josephus (Perseus TEI) and Philo (First1KGreek TEI), witnesses `Josephus` / `Philo`:
  ref   `<Work>.<book>.<section>` (always 3 parts, letters-only work abbreviation) from the nesting of
        `div[@type='textpart']/@n`. Single-level works (Vita, most Philo) use book `1`. Sections whose `n`
        is not numeric (e.g. Ant book 1 `n="arg"`, a summary) are skipped and counted.
  text  text of each leaf section minus <head>, <label>, <note> (headings, apparatus) and <sic> when paired with a sibling <corr>;
        <q>, <add>, <corr> and <del> content is kept (Perseus <del> = editor-bracketed transmitted text, e.g.
        Ant 18.63-64; its words get editions='bracketed'). Whitespace collapsed.
  words one row per whitespace token, surface = token with punctuation stripped, lemma '' (TEI has none),
        pos = 1-based index within the section.

Moulton & Milligan (noisy OCR) -> `papyri_vocab(lemma, entry)`; meta papyri_quality = noisy-ocr.
Entries are split on headword lines: a line that is a single Greek word ending with `.` or `,`.
Bare running-head lemma lines (no trailing punctuation) are ignored. Skipped if absent or deferred.
"""
import json
import lzma
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

from otslib import norm

TEI = "{http://www.tei-c.org/ns/1.0}"
_SKIP = {TEI + t for t in ("head", "label", "note")}

JOSEPHUS = {"tlg001": "Ant", "tlg002": "Life", "tlg003": "AgAp", "tlg004": "War"}
PHILO = {
    "tlg001": "Opif", "tlg002": "LegAll", "tlg003": "Cher", "tlg004": "Sacr", "tlg005": "Det",
    "tlg006": "Post", "tlg007": "Gig", "tlg008": "Deus", "tlg009": "Agr", "tlg010": "Plant",
    "tlg011": "Ebr", "tlg012": "Sobr", "tlg013": "Conf", "tlg014": "Migr", "tlg015": "Her",
    "tlg016": "Congr", "tlg017": "Fug", "tlg018": "Mut", "tlg019": "Somn", "tlg020": "Abr",
    "tlg021": "Ios", "tlg022": "Mos", "tlg023": "Decal", "tlg024": "SpecLeg", "tlg025": "Virt",
    "tlg026": "Praem", "tlg027": "Prob", "tlg028": "Contempl", "tlg029": "Aet", "tlg030": "Flacc",
    "tlg031": "Legat",
}
_ELISION = "’᾽ʼ'"


def _text(el, out, br=False):
    """Append (text, bracketed) pairs for el's content; <del> content is flagged bracketed."""
    if el.tag in _SKIP:
        return
    br = br or el.tag == TEI + "del"
    if el.text:
        out.append((el.text, br))
    has_corr = any(c.tag == TEI + "corr" for c in el)
    for c in el:
        if not (c.tag == TEI + "sic" and has_corr):
            _text(c, out, br)
        if c.tail:
            out.append((c.tail, br))


def _tokens(pairs):
    """Whitespace-split text from (text, bracketed) pairs -> [(token, bracketed)], NFC."""
    toks, cur, flag = [], [], False
    for txt, br in pairs:
        for ch in txt:
            if ch.isspace():
                if cur:
                    toks.append(("".join(cur), flag))
                    cur, flag = [], False
            else:
                cur.append(ch)
                flag = flag or br
    if cur:
        toks.append(("".join(cur), flag))
    return [(norm.nfc(t), f) for t, f in toks]


def _surface(tok):
    return "".join(c for c in tok if c in _ELISION or not (unicodedata.category(c)[0] in "PS"))


def _sections(div, path, out, skipped):
    """Collect (path of n values, text) for leaf textparts."""
    parts = [c for c in div if c.tag == TEI + "div" and c.get("type") == "textpart"]
    if not parts:
        buf = []
        _text(div, buf)
        out.append((path, _tokens(buf)))
        return
    for p in parts:
        _sections(p, path + [p.get("n", "")], out, skipped)


def _load_tei(conn, path, witness, work, stats):
    root = ET.fromstring(lzma.open(path, "rb").read())
    ed = root.find(f".//{TEI}div[@type='edition']")
    secs = []
    _sections(ed, [], secs, stats)
    verses, words = {}, []
    for ns, toks in secs:
        text = toks
        if len(ns) == 1:
            ns = ["1"] + ns
        if len(ns) != 2 or not all(n.isdigit() for n in ns) or not toks:
            stats["skipped"] += 1
            continue
        ref = f"{work}.{int(ns[0])}.{int(ns[1])}"
        verses.setdefault(ref, []).extend(toks)
    for ref, toks in verses.items():
        text = norm.display(" ".join(t for t, _ in toks), "grc")
        conn.execute("INSERT INTO verses VALUES (?,?,?,?,?)",
                     ("ext", witness, ref, text, norm.match_key(text, "grc")))
        pos = 0
        for tok, br in toks:
            sf = _surface(tok)
            if not sf:
                continue
            pos += 1
            words.append(("ext", witness, ref, pos, sf, "", "", "", "", "bracketed" if br else "", "", ""))
    conn.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", words)
    stats["verses"][witness] += len(verses)
    stats["words"][witness] += len(words)


def _headword(line):
    s = line.strip()
    if len(s) < 2 or s[-1] not in ".,":
        return None
    w = s[:-1]
    if not re.fullmatch(r"[Ͱ-Ͽἀ-῿]+", w):
        return None
    return norm.nfc(w)


MM_MIN_BODY = 20  # chars; shorter bodies are OCR debris (empty or split-off headwords)


MM_XREF = re.compile(r"See( also| s\.v\.)? [Ͱ-Ͽἀ-῿]")  # "See s.v. ἀγγεῖον." is a real, short entry


def _keep_mm(lemma, body):
    """Drop OCR noise: bodies < 20 chars unless a cross-reference; headwords <= 2 chars unless real Greek letters."""
    if len(body.strip()) < MM_MIN_BODY and not MM_XREF.match(body.strip()):
        return False
    return any(unicodedata.category(ch).startswith("L") for ch in lemma) and (
        len(lemma) > 2 or all(unicodedata.category(ch).startswith("L") for ch in lemma))


def _load_mm(conn, path):
    raw, cur, body = [], None, []
    for line in lzma.open(path, "rt", encoding="utf-8-sig"):
        hw = _headword(line)
        if hw:
            if cur:
                raw.append((cur, "\n".join(body).strip()))
            cur, body = hw, []
        elif cur is not None:
            body.append(line.rstrip("\n"))
    if cur:
        raw.append((cur, "\n".join(body).strip()))
    merged = {}  # OCR re-splits one entry into several: merge same-lemma bodies
    for lemma, entry in raw:
        if _keep_mm(lemma, entry):
            merged.setdefault(lemma, []).append(entry)
    entries = [(lemma, "\n---\n".join(parts)) for lemma, parts in merged.items()]
    conn.executemany("INSERT INTO papyri_vocab VALUES (?,?)", entries)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_papyri_lemma ON papyri_vocab (lemma)")
    conn.execute("DELETE FROM meta WHERE key='papyri_quality'")
    conn.execute("INSERT INTO meta VALUES ('papyri_quality','noisy-ocr')")
    return len(entries), len(raw)


def _mm_deferred(sources_dir):
    try:
        man = json.loads((sources_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for f in man.get("entries", []) if isinstance(man, dict) else []:
        if isinstance(f, dict) and f.get("path", "").endswith("moulton-milligan.txt.xz"):
            return f.get("status") == "deferred"
    return False


def load(conn, sources_dir, out=None):
    import sys
    from collections import Counter
    out = out or sys.stdout
    sources_dir = Path(sources_dir)
    stats = {"verses": Counter(), "words": Counter(), "skipped": 0}
    for sub, witness, table in (("josephus", "Josephus", JOSEPHUS), ("philo", "Philo", PHILO)):
        for p in sorted((sources_dir / "ext" / sub).glob("*.xz")):
            m = re.search(r"\.(tlg\d{3})\.", p.name)
            work = table.get(m.group(1)) if m else None
            if not work:
                print(f"ext: skipped {p.name} (no work abbreviation)", file=out)
                continue
            _load_tei(conn, p, witness, work, stats)
    mm = sources_dir / "ext" / "moulton-milligan.txt.xz"
    n_mm = raw_mm = 0
    if _mm_deferred(sources_dir) or not mm.is_file():
        print("ext: Moulton-Milligan skipped (deferred or missing)", file=out)
    else:
        n_mm, raw_mm = _load_mm(conn, mm)
    for w in ("Josephus", "Philo"):
        print(f"ext {w}: {stats['verses'][w]} verses, {stats['words'][w]} words", file=out)
    print(f"ext: {stats['skipped']} sections skipped (non-numeric ref or empty); {n_mm} papyri entries "
          f"(from {raw_mm} OCR entries; noise dropped, duplicates merged)", file=out)
    return sum(stats["words"].values()) + sum(stats["verses"].values()) + n_mm
