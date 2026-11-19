#!/usr/bin/env python3
"""Validate sermon files: original-language quotes must exist in the local DB, translation lines must
avoid tradition vocabulary, template sections and frontmatter must be present.

Usage: check_sermon.py <file>... [--db PATH] [--quotes-only [--lang xx]]
--quotes-only: for chat answers (word studies, single-verse questions) — checks only quote tags, quoted
text, Literal:/Natural: lines and tradition vocabulary (language from --lang, default en); no
frontmatter, sections, Notes or length checks.
Output: `ERROR <line>: <msg>` / `WARN <line>: <msg>` (with a `<path>:` header when several files).
Exit: 1 if any ERROR, 2 if bible.db is missing, else 0.
"""
import argparse
import re
import sqlite3
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
HAS_SCRIPT = re.compile("[\u0370-\u03ff\u1f00-\u1fff\u0590-\u05ff]")
SCRIPT_WORD = "[\u0300-\u036f\u0370-\u03ff\u1f00-\u1fff\u0590-\u05ff]+"
PROSE_RUN = re.compile(rf"{SCRIPT_WORD}(?:[\s,.;\u00b7:\u05c3]+{SCRIPT_WORD}){{2,}}")
TEMPLATE_NAME = re.compile(r"^[a-z0-9-]+$")
MAX_RANGE = 50
MAX_ELLIPSES = 4
LANGS = {"es": "es", "spanish": "es", "español": "es", "espanol": "es", "castellano": "es", "spa": "es",
         "en": "en", "english": "en", "inglés": "en", "ingles": "en", "eng": "en"}
LANG_CODE = re.compile(r"^[a-z]{2,3}(?:[-_][a-z0-9]+)*$")
CHECKED_LANGS = ("es", "en")  # languages with a tradition-vocabulary list; others are scanned with both
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
    """-> (verse refs present for corpus+witness in order, set of refs the tag names, error|None)."""
    if corpus == "ext":
        wanted = [ref_text.strip()]
    else:
        try:
            r = parse_ref(ref_text)
        except RefError:
            return [], set(), f"unknown ref: {ref_text}"
        if r.verse is None:
            return [], set(), f"chapter-only ref {ref_text}: use Book.Chapter.Verse (or a verse range)"
        end = r.verse_end or r.verse
        if end < r.verse:
            return [], set(), f"reversed verse range: {ref_text}"
        if end - r.verse + 1 > MAX_RANGE:
            return [], set(), f"verse range {ref_text} too long (max {MAX_RANGE} verses)"
        wanted = [f"{r.book}.{r.chapter}.{v}" for v in range(r.verse, end + 1)]
    present = [ref for ref in wanted
               if conn.execute("SELECT 1 FROM verses WHERE corpus=? AND witness=? AND ref=? LIMIT 1",
                               (corpus, witness, ref)).fetchone()]
    missing = [r for r in wanted if r not in present]
    if missing:
        shown = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
        return present, set(wanted), (f"verse(s) {shown} not found for {corpus} witness {witness} "
                                      "(unknown ref, or the verse is absent in this witness)")
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
    """-> (error message | None, [warning messages])."""
    original = nfc(original)
    segs = [s for s in re.split(r"…|\.\.\.", original) if s.strip()]
    if not segs:
        return "empty quote", []
    warns = []
    if len(segs) > 1 and any(len(s.split()) == 1 for s in segs):
        warns.append("quote has one-word segments around an ellipsis (stitching risk): quote a contiguous phrase")
    if len(re.findall(r"…|\.\.\.", original)) > MAX_ELLIPSES:
        warns.append(f"quote has more than {MAX_ELLIPSES + 1} segments (stitching risk): split it into separate quotes")
    hay = haystack(conn, corpus, witness, hay_refs, lang)
    keys = [match_key(s, lang) for s in segs]
    miss = find_in_order(hay, keys)
    if miss is not None and lang == "heb" and not any(HEB_POINT.search(s) for s in segs):
        miss = find_in_order(strip_points(hay), keys)  # unpointed quote vs pointed verse
    if miss is None:
        return None, warns
    span = hay_refs[0] if len(hay_refs) == 1 else f"{hay_refs[0]}..{hay_refs[-1]}"
    shown = next((s.strip() for s, k in zip(segs, keys) if k == miss), miss)
    return f"quoted text not found in {corpus}/{witness} {span}: {shown[:60]}", warns


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
    """Blockquote scan -> (quotes, problems).

    quotes: dicts(line, tag, original, labels={'literal': [(line, text)], 'natural': [...]}).
    problems: (line, msg) for tag-like lines that do not parse and for original-language text that
    is not the original line(s) of a tagged quote. Continuation lines after a label extend it.
    """
    quotes, problems, cur, last = [], [], None, None
    for i in range(start, len(lines)):
        raw = lines[i].lstrip()
        if not raw.startswith(">"):
            cur = last = None
            continue
        content = raw
        while content.startswith(">"):
            content = content[1:].lstrip()
        ln = i + 1
        m = TAG_RE.match(content)
        if m:
            cur = {"line": ln, "tag": m.groups()[:3], "original": m.group(4), "labels": {}}
            quotes.append(cur)
            last = None
            continue
        if content.lstrip("*_ ").startswith("["):
            problems.append((ln, "unparseable quote tag: expected `> [CORPUS[:WITNESS] Ref] original`"))
            cur = last = None
            continue
        lm = LABEL_RE.match(content)
        if lm and cur is not None:
            last = [ln, lm.group(2)]
            cur["labels"].setdefault(lm.group(1).lower(), []).append(last)
            if HAS_SCRIPT.search(lm.group(2)):
                problems.append((ln, "untagged original-language text on a translation line"))
        elif cur is not None and last is None and not cur["labels"]:
            cur["original"] += " " + content  # original continued on the next `>` line
        elif last is not None:
            last[1] += " " + content
            if HAS_SCRIPT.search(content):
                problems.append((ln, "untagged original-language text in quote block"))
        elif HAS_SCRIPT.search(content):
            problems.append((ln, "untagged original-language text in blockquote: tag it `[CORPUS Ref]` so it can be verified"))
    return quotes, problems


def required_sections(fm, lang):
    tpl = fm.get("template", "")
    if tpl == "custom":
        names = [s.strip() for s in fm.get("sections", "").split(",") if s.strip()]
        return [(n, n) for n in names], None if names else "template custom requires `sections:` in frontmatter"
    if not TEMPLATE_NAME.match(tpl) or tpl == "sermon-output" or not (references.TEMPLATES / f"{tpl}.md").is_file():
        return [], f"unknown template: {tpl!r} (use a template name from templates/, or `custom`)"
    en = references.template_sections(tpl)
    if not en:
        return [], f"template {tpl!r} declares no sections"
    loc = references.template_sections(tpl, lang)
    if len(loc) != len(en):
        loc = en
    return list(zip(loc, en)), None


def notes_heading(headings, pairs):
    """Index into headings of the Notes section, or None."""
    starts = lambda h, names: any(h.lower().startswith(n.lower()) for n in names)
    if pairs:
        i = 0
        for k, names in enumerate(pairs):
            while i < len(headings) and not starts(headings[i][1], names):
                i += 1
            if i == len(headings):
                break
            if k == len(pairs) - 1:
                return i
            i += 1
    exact = {"notes", "notas"} | {n.lower() for n in (pairs[-1] if pairs else ())}
    for idx, (_, h) in enumerate(headings):
        if h.lower() in exact:
            return idx
    for idx, (_, h) in enumerate(headings):
        if re.match(r"(notes|notas)\b", h, re.IGNORECASE):
            return idx
    return None


def tradition_regex(*langs):
    terms = sorted(set().union(*(references.tradition_terms(lg) for lg in langs)), key=len, reverse=True)
    if not terms:
        return None
    def word(w):  # straight and curly apostrophes are interchangeable
        return "['\u2019]".join(re.escape(x) for x in re.split("['\u2019]", w))

    alts = [r"\s+".join(word(w) for w in t.split()) for t in terms]
    return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)


# ---------------------------------------------------------------- main check

def quoted_already(run, quotes, line):
    """True if `run` (prose original-language words) appears verbatim in a quote block above `line`."""
    lg = "heb" if re.search("[\u0590-\u05ff]", run) else "grc"
    k = f" {match_key(run, lg)} "
    return any(q["line"] < line and k in f" {match_key(nfc(q['original']), lg)} " for q in quotes)


def check(path, conn, quotes_only=False, lang=None):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    body_start, has_fm = split_frontmatter(lines)
    fm = references.frontmatter(path) if has_fm else {}
    if quotes_only:
        fm = {"language": lang or fm.get("language") or "en"}
    for k in () if quotes_only else REQUIRED_KEYS:
        if not fm.get(k):
            out.append(Finding("ERROR", 1, f"missing frontmatter key: {k}"))
    # Any language may be written; tradition vocabulary is only machine-checked where the
    # reference table has terms for it (es, en). Other languages get a WARN, quotes are still verified.
    raw_lang = (fm.get("language") or "en").strip().lower()
    lang = LANGS.get(raw_lang) or LANGS.get(re.split(r"[-_]", raw_lang)[0])
    if lang is None and not LANG_CODE.match(raw_lang):
        out.append(Finding("ERROR", 1, f"invalid language value {fm.get('language')!r}: use a language code "
                           "such as es, en, pt, pt-BR"))
    elif lang is None:
        lang = re.split(r"[-_]", raw_lang)[0]
    if lang and references.tradition_terms(lang):
        trad_langs = (lang,)
    else:
        # unknown or invalid language: still scan with the es and en lists, so a mislabelled Spanish or
        # English sermon cannot skip the check; the rest of the language's vocabulary is unchecked
        trad_langs = CHECKED_LANGS
        if lang:
            out.append(Finding("WARN", 1, f"tradition vocabulary not checked for {lang} (only "
                               f"{', '.join(CHECKED_LANGS)} have a list; translation lines scanned with the es/en "
                               "lists only): review Literal:/Natural: lines by hand"))
    lang = lang or "en"

    headings = [(i + 1, m.group(1)) for i in range(body_start, len(lines)) if (m := H2_RE.match(lines[i]))]
    pairs = []
    if fm.get("template"):
        # named templates: localized `sections_<lang>` if the template has them, else the English names;
        # `custom`: the `sections:` list as written (any language)
        pairs, err = required_sections(fm, lang)
        if err:
            out.append(Finding("ERROR", 1, err))
        for loc, en in pairs:
            ok = any(h.lower().startswith(loc.lower()) or h.lower().startswith(en.lower()) for _, h in headings)
            if not ok:
                out.append(Finding("ERROR", 1, f"missing section: ## {loc}" + (f" ({en})" if loc != en else "")))

    # notes section: the heading matched by the template's last section when the sections are walked in
    # order (so an earlier heading sharing its prefix is not taken); else an exact Notes/Notas/last-name
    # heading; else the first heading starting with Notes/Notas
    notes_idx = None if quotes_only else notes_heading(headings, pairs)
    notes_lines, notes_range = [], None
    if notes_idx is not None:
        ln = headings[notes_idx][0]
        end = headings[notes_idx + 1][0] - 1 if notes_idx + 1 < len(headings) else len(lines)
        notes_range = (ln, end)
        notes_lines = lines[ln:end]

    notes_verses = refs_in_text("\n".join(notes_lines))
    contested = contested_verses()
    trad = tradition_regex(*trad_langs)
    trad_src = "" if trad_langs == (lang,) else " (es/en list)"

    # quotes
    quotes, problems = parse_quotes(lines, body_start)
    out += [Finding("ERROR", ln, msg) for ln, msg in problems]
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
                        lg = "heb" if corpus in ("hebot", "dss") else "grc"
                        msg, warns = check_quote(conn, corpus, canon, hay_refs, q["original"], lg)
                        if msg:
                            out.append(Finding("ERROR", q["line"], msg))
                        out += [Finding("WARN", q["line"], w) for w in warns]
                        if corpus != "ext" and not quotes_only:
                            hit = (set(hay_refs) | named) & contested
                            miss = sorted(hit - notes_verses)
                            if miss:
                                out.append(Finding("WARN", q["line"],
                                                   f"contested reading {', '.join(miss)} quoted without a mention in Notes"))
        for label in ("literal", "natural"):
            if label not in q["labels"]:
                out.append(Finding("ERROR", q["line"], f"missing {label.capitalize()}: line after quote"))
    for q in quotes:
        for label, entries in q["labels"].items():
            for ln, text in entries:
                for m in (trad.finditer(nfc(text)) if trad else ()):
                    out.append(Finding("ERROR", ln, f"tradition term {m.group(0)!r}{trad_src} on {label.capitalize()}: line; use a plain rendering (discuss the term in prose or Notes)"))

    # runs of original-language words in prose (outside any blockquote) should be tagged quotes
    for i in range(body_start, len(lines)):
        if lines[i].lstrip().startswith(">") or (notes_range and notes_range[0] <= i + 1 <= notes_range[1]):
            continue  # quote blocks are verified; Notes legitimately cite variant phrases
        if any(not quoted_already(m.group(0), quotes, i + 1) for m in PROSE_RUN.finditer(nfc(lines[i]))):
            out.append(Finding("WARN", i + 1, "3+ original-language words in prose: put the phrase in a tagged quote block so it is verified"))

    if quotes_only:
        return sorted(out, key=lambda f: (f.line, f.level != "ERROR"))

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
    ap.add_argument("--quotes-only", action="store_true", help="chat answers: check quotes/tags/tradition terms only")
    ap.add_argument("--lang", help="language of the Literal:/Natural: lines in --quotes-only mode (default en)")
    a = ap.parse_args(argv)
    if a.db:
        p = Path(a.db)
        if not p.is_file():
            print(db.MISSING_MSG, file=sys.stderr)
            return 2
        conn = db.connect(p)
    else:
        conn = db.require_db()
    try:
        conn.execute("SELECT 1 FROM verses LIMIT 1").fetchall()
    except sqlite3.DatabaseError:
        print("not a valid bible.db (no readable verses table); rebuild with python3 scripts/build_db.py", file=sys.stderr)
        return 2
    bad = False
    for f in a.files:
        try:
            findings = check(Path(f), conn, quotes_only=a.quotes_only, lang=a.lang)
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
