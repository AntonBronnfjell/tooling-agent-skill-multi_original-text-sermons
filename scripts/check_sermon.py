#!/usr/bin/env python3
"""Validate sermon files: original-language quotes must exist in the local DB, translation lines must
avoid tradition vocabulary, template sections and frontmatter must be present.

Usage: check_sermon.py <file>... [--db PATH]
Output: `ERROR <line>: <msg>` / `WARN <line>: <msg>` (with a `<path>:` header when several files).
Exit: 1 if any ERROR, 2 if bible.db is missing, else 0.
"""
import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from otslib import db, references  # noqa: E402
from otslib.norm import match_key, nfc, strip_points  # noqa: E402
from otslib.refs import RefError, parse_ref  # noqa: E402

REQUIRED_KEYS = ("passage", "language", "specialization", "audience", "template", "date")
CORPUS = {"HEB": "hebot", "ARC": "hebot", "GRC": "grnt", "LXX": "lxx", "DSS": "dss", "EXT": "ext"}
DEFAULT_WITNESS = {"hebot": "WLC", "grnt": "SBL", "lxx": "Rahlfs"}
WORDS_MIN, WORDS_MAX = 500, 1300

TAG_RE = re.compile(r"^\[([A-Za-z]+)(?::([^\s\]]+))?\s+([^\]]+?)\s*\]\s*(.*)$")
LABEL_RE = re.compile(r"^(Literal|Natural)\s*:\s*(.*)$", re.IGNORECASE)
H2_RE = re.compile(r"^##(?!#)\s*(.*?)\s*$")
OSIS_IN_TEXT = re.compile(r"(?<![\w.])((?:[1-3])?[A-Za-z]+\.\d+\.\d+(?:\s*[-–]\s*\d+)?)")
HUMAN_IN_TEXT = re.compile(r"(?<![\w.])((?:[1-3]\s?)?[^\W\d_]+\.?)\s+(\d+):(\d+)(?:\s*[-–]\s*(\d+))?")
HEB_POINT = re.compile("[ְ-ׇּֿׁׂ]")


class Finding(NamedTuple):
    level: str
    line: int
    msg: str


# ---------------------------------------------------------------- refs

def verses_of(ref):
    """OSIS verse refs covered by a parsed Ref (empty for a whole chapter)."""
    if ref.verse is None:
        return set()
    end = min(ref.verse_end or ref.verse, ref.verse + 300)
    return {f"{ref.book}.{ref.chapter}.{v}" for v in range(ref.verse, end + 1)}


def contested_verses():
    out = set()
    for r in references.contested_refs():
        try:
            out |= verses_of(parse_ref(r))
        except RefError:
            out.add(r)
    return out


def refs_in_text(text):
    out = set()
    for m in OSIS_IN_TEXT.finditer(text):
        try:
            out |= verses_of(parse_ref(re.sub(r"\s+", "", m.group(1))))
        except RefError:
            pass
    for m in HUMAN_IN_TEXT.finditer(text):
        s = f"{m.group(1)} {m.group(2)}:{m.group(3)}" + (f"-{m.group(4)}" if m.group(4) else "")
        try:
            out |= verses_of(parse_ref(s))
        except RefError:
            pass
    return out


# ---------------------------------------------------------------- matching

def resolve_witness(conn, corpus, w):
    names = [r[0] for r in conn.execute("SELECT DISTINCT witness FROM verses WHERE corpus=?", (corpus,))]
    for n in names:
        if n.casefold() == w.casefold():
            return n
    return None


def quote_refs(conn, corpus, witness, ref_text):
    """-> (list of verse refs present for corpus+witness in order, set of refs the tag names, error|None)."""
    if corpus == "ext":
        wanted = [ref_text.strip()]
    else:
        try:
            r = parse_ref(ref_text)
        except RefError:
            return [], set(), f"unknown ref: {ref_text}"
        if r.verse is None:
            rows = conn.execute("SELECT ref FROM verses WHERE corpus=? AND witness=? AND ref LIKE ?",
                                (corpus, witness, f"{r.book}.{r.chapter}.%")).fetchall()
            wanted = sorted({x[0] for x in rows}, key=lambda s: int(s.rsplit(".", 1)[1]))
        else:
            wanted = [f"{r.book}.{r.chapter}.{v}" for v in range(r.verse, (r.verse_end or r.verse) + 1)]
    present = []
    for ref in wanted:
        if conn.execute("SELECT 1 FROM verses WHERE corpus=? AND witness=? AND ref=? LIMIT 1",
                        (corpus, witness, ref)).fetchone():
            present.append(ref)
    if not present:
        return [], set(wanted), f"ref {ref_text} not found for {corpus} witness {witness} (unknown ref or absent in this witness)"
    return present, set(wanted), None


def haystack(conn, corpus, witness, refs, lang):
    keys = []
    for ref in refs:
        for text, mk in conn.execute("SELECT text, match_key FROM verses WHERE corpus=? AND witness=? AND ref=?",
                                     (corpus, witness, ref)):
            keys.append(mk or match_key(text, lang))
    return " ".join(keys)


def find_in_order(hay, segments):
    """Each segment must occur (on word boundaries) after the previous one. -> first missing segment | None."""
    pos = 0
    for seg in segments:
        found = -1
        i = hay.find(seg, pos)
        while i != -1:
            end = i + len(seg)
            if (i == 0 or hay[i - 1] == " ") and (end == len(hay) or hay[end] == " "):
                found = i
                break
            i = hay.find(seg, i + 1)
        if found < 0:
            return seg
        pos = found + len(seg)
    return None


def check_quote(conn, corpus, witness, hay_refs, original, lang):
    segs = [s for s in re.split(r"…|\.\.\.", nfc(original)) if s.strip()]
    if not segs:
        return "empty quote"
    hay = haystack(conn, corpus, witness, hay_refs, lang)
    keys = [match_key(s, lang) for s in segs]
    miss = find_in_order(hay, keys)
    if miss is not None and lang == "heb" and not any(HEB_POINT.search(s) for s in segs):
        miss = find_in_order(strip_points(hay), keys)  # unpointed quote vs pointed verse
    if miss is None:
        return None
    span = hay_refs[0] if len(hay_refs) == 1 else f"{hay_refs[0]}..{hay_refs[-1]}"
    shown = next((s.strip() for s, k in zip(segs, keys) if k == miss), miss)
    return f"quoted text not found in {corpus}/{witness} {span}: {shown[:60]}"


# ---------------------------------------------------------------- parsing

def split_frontmatter(lines):
    """-> (index of first body line, has_frontmatter)."""
    if not lines or lines[0].strip() != "---":
        return 0, False
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1, True
    return len(lines), True


def parse_quotes(lines, start):
    """Quote blocks -> list of dicts(line, tag, original, literal, natural, label_lines)."""
    quotes, cur = [], None
    for i in range(start, len(lines)):
        raw = lines[i]
        if not raw.lstrip().startswith(">"):
            cur = None
            continue
        content = raw.lstrip()[1:].strip()
        m = TAG_RE.match(content)
        if m:
            cur = {"line": i + 1, "tag": m.groups()[:3], "original": m.group(4), "labels": {}}
            quotes.append(cur)
            continue
        if cur is None:
            continue
        lm = LABEL_RE.match(content)
        if lm:
            cur["labels"][lm.group(1).lower()] = (i + 1, lm.group(2))
        elif not cur["labels"]:
            cur["original"] += " " + content
    return quotes


def required_sections(fm, lang):
    tpl = fm.get("template", "")
    if tpl == "custom":
        names = [s.strip() for s in fm.get("sections", "").split(",") if s.strip()]
        return [(n, n) for n in names], None if names else "template custom requires `sections:` in frontmatter"
    if not (references.TEMPLATES / f"{tpl}.md").is_file():
        return [], f"unknown template: {tpl!r}"
    en = references.template_sections(tpl)
    loc = references.template_sections(tpl, lang)
    if len(loc) != len(en):
        loc = en
    return list(zip(loc, en)), None


def tradition_regex(lang):
    terms = sorted(references.tradition_terms(lang), key=len, reverse=True)
    if not terms:
        return None
    def word(w):  # straight and curly apostrophes are interchangeable
        return "['\u2019]".join(re.escape(x) for x in re.split("['\u2019]", w))

    alts = [r"\s+".join(word(w) for w in t.split()) for t in terms]
    return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)


# ---------------------------------------------------------------- main check

def check(path, conn):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    body_start, has_fm = split_frontmatter(lines)
    fm = references.frontmatter(path) if has_fm else {}
    for k in REQUIRED_KEYS:
        if not fm.get(k):
            out.append(Finding("ERROR", 1, f"missing frontmatter key: {k}"))
    lang = (fm.get("language") or "en").lower()[:2]

    # headings / notes section
    headings = [(i + 1, m.group(1)) for i in range(body_start, len(lines)) if (m := H2_RE.match(lines[i]))]
    notes_lines, notes_range = [], None
    for idx, (ln, h) in enumerate(headings):
        if re.match(r"(notes|notas)\b", h, re.IGNORECASE):
            end = headings[idx + 1][0] - 1 if idx + 1 < len(headings) else len(lines)
            notes_range = (ln, end)
            notes_lines = lines[ln:end]
            break

    if fm.get("template"):
        pairs, err = required_sections(fm, lang)
        if err:
            out.append(Finding("ERROR", 1, err))
        for loc, en in pairs:
            ok = any(h.lower().startswith(loc.lower()) or h.lower().startswith(en.lower()) for _, h in headings)
            if not ok:
                out.append(Finding("ERROR", 1, f"missing section: ## {loc}" + (f" ({en})" if loc != en else "")))

    notes_verses = refs_in_text("\n".join(notes_lines))
    contested = contested_verses()
    trad = tradition_regex(lang)

    # quotes
    quotes = parse_quotes(lines, body_start)
    for q in quotes:
        tag, wit, ref_text = q["tag"]
        corpus = CORPUS.get(tag.upper())
        if corpus is None:
            out.append(Finding("ERROR", q["line"], f"unknown corpus tag: {tag}"))
        else:
            witness = wit or DEFAULT_WITNESS.get(corpus)
            if witness is None:
                out.append(Finding("ERROR", q["line"], f"{tag.upper()} quote requires a witness, e.g. [{tag.upper()}:<witness> {ref_text}]"))
            else:
                canon = resolve_witness(conn, corpus, witness)
                if canon is None:
                    out.append(Finding("ERROR", q["line"], f"unknown witness {witness!r} for {tag.upper()}"))
                else:
                    hay_refs, named, err = quote_refs(conn, corpus, canon, ref_text)
                    if err:
                        out.append(Finding("ERROR", q["line"], err))
                    else:
                        lg = "heb" if corpus == "hebot" else "grc"
                        msg = check_quote(conn, corpus, canon, hay_refs, q["original"], lg)
                        if msg:
                            out.append(Finding("ERROR", q["line"], msg))
                        if corpus != "ext":
                            hit = (set(hay_refs) | named) & contested
                            miss = sorted(hit - notes_verses)
                            if miss:
                                out.append(Finding("WARN", q["line"],
                                                   f"contested reading {', '.join(miss)} quoted without a mention in Notes"))
        for label in ("literal", "natural"):
            if label not in q["labels"]:
                out.append(Finding("ERROR", q["line"], f"missing {label.capitalize()}: line after quote"))
    for q in quotes:
        for label, (ln, text) in q["labels"].items():
            if trad:
                for m in trad.finditer(nfc(text)):
                    out.append(Finding("ERROR", ln, f"tradition term {m.group(0)!r} on {label.capitalize()}: line; use a plain rendering (discuss the term in prose or Notes)"))

    # word count (excluding frontmatter, quote blocks, headings, Notes)
    words = 0
    for i in range(body_start, len(lines)):
        ln = i + 1
        s = lines[i].strip()
        if not s or s.startswith(">") or s.startswith("#"):
            continue
        if notes_range and notes_range[0] <= ln <= notes_range[1]:
            continue
        words += len(re.findall(r"[\w'’-]+", s))
    if words < WORDS_MIN or words > WORDS_MAX:
        out.append(Finding("WARN", 1, f"body word count {words} outside {WORDS_MIN}-{WORDS_MAX} (about 15-20 min spoken)"))

    return sorted(out, key=lambda f: (f.line, f.level != "ERROR"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    if a.db:
        p = Path(a.db)
        if not p.is_file():
            print(db.MISSING_MSG, file=sys.stderr)
            return 2
        conn = db.connect(p)
    else:
        conn = db.require_db()
    bad = False
    for f in a.files:
        try:
            findings = check(Path(f), conn)
        except (OSError, UnicodeDecodeError) as e:
            print(f"ERROR 0: cannot read {f}: {e}")
            bad = True
            continue
        if len(a.files) > 1:
            print(f"{f}:")
        for x in findings:
            print(f"{x.level} {x.line}: {x.msg}")
        bad = bad or any(x.level == "ERROR" for x in findings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
