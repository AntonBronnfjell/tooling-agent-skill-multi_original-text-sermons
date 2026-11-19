#!/usr/bin/env python3
"""Validate sermon files: original-language quotes must exist in the local DB, translation lines must
avoid tradition vocabulary, template sections and frontmatter must be present.

Usage: check_sermon.py <file>... [--db PATH] [--quotes-only [--lang xx]]
--quotes-only: for chat answers (word studies, single-verse questions) — checks only quote tags, quoted
text, inline-tagged text, untagged original-language runs, Literal:/Natural: lines and tradition vocabulary
(language from --lang, default en); any frontmatter is ignored (read as text); no sections, Notes or length
checks; an answer with no tagged quote at all is an ERROR.
Original-language text anywhere in the body (Notes included): a run of 2+ Greek/Hebrew words must be a
tagged quote block or carry an inline tag right before it, `[CORPUS[:WITNESS] Ref] <original text>`, which
is verified like a quote; single words (lemmas) are free; a run already quoted verbatim above is exempt.
Output: `ERROR <line>: <msg>` / `WARN <line>: <msg>` (with a `<path>:` header when several files), then
`OK <path>` for each file without errors.
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
from otslib.refs import CrossChapterError, RefError, parse_ref  # noqa: E402

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
SCRIPT_WORD = "[\u0300-\u036f\u0370-\u03ff\u1f00-\u1fff\u0590-\u05ff]+[\u2019\u02bc']?"
SCRIPT_RUN = re.compile(rf"{SCRIPT_WORD}(?:[\s,.;\u00b7:\u05c3\u2026]+{SCRIPT_WORD})*")
SCRIPT_TOKEN = re.compile(SCRIPT_WORD)
INLINE_TAG = re.compile(r"\[(" + "|".join(CORPUS) + r")(?::([^\s\]]+))?\s+([^\]]+?)\s*\]\s*$", re.IGNORECASE)
EDITOR_NOTE = re.compile(r"bracket|corchete|editor", re.IGNORECASE)
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
        except CrossChapterError as e:
            return [], set(), str(e)
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


def order_findings(conn, corpus, witness, refs, line):
    """Findings for `order_flags` on the quoted Greek verses. A TR quote of a known-scrambled verse is an
    error; any other flag but the informational KJV verse-break move warns."""
    if corpus != "grnt":
        return []
    try:
        rows = conn.execute("SELECT ref, reason FROM order_flags WHERE corpus=? AND witness=? AND ref IN (%s)"
                            % ",".join("?" * len(refs)), (corpus, witness, *refs)).fetchall()
    except sqlite3.OperationalError:  # DB built before order_flags existed
        return []
    out = []
    for ref in refs:
        why = {r[1] for r in rows if r[0] == ref}
        if "known scrambled" in why:
            out.append(Finding("ERROR", line, f"{witness} word order for {ref} is known to be wrong in the data; "
                                              "quote another witness"))
        elif why - {"verse break follows KJV"}:
            out.append(Finding("WARN", line, f"order uncertain for {witness} {ref}: verify against a printed edition"))
    return out


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
    """-> (index of first body line, has_frontmatter, terminated). An unterminated block is reported by the
    caller; its body is read from line 2 on so that nothing after the opening `---` escapes the checks."""
    if not lines or lines[0].strip() != "---":
        return 0, False, True
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1, True, True
    return 1, True, False


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

    def term(t):  # `stem*` rows match every word starting with the stem
        if t.endswith("*"):
            return word(t[:-1]) + r"\w*"
        return r"\s+".join(word(w) for w in t.split())

    alts = [term(t) for t in terms]
    return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)


# ---------------------------------------------------------------- main check

def quoted_already(run, quotes, line):
    """True if `run` (prose original-language words) appears verbatim in a verified quote above `line`."""
    lg = "heb" if re.search("[\u0590-\u05ff]", run) else "grc"
    k = f" {match_key(run, lg)} "
    return any(q["line"] < line and k in f" {match_key(nfc(q['original']), lg)} " for q in quotes)


def ext_bracketed(conn, witness, refs, original):
    """True if the quoted words (matched in order, segment by segment) include an editor-bracketed EXT word."""
    words = []
    for ref in refs:
        words += conn.execute("SELECT surface, editions FROM words WHERE corpus='ext' AND witness=? AND ref=? "
                              "ORDER BY pos", (witness, ref)).fetchall()
    keys = [match_key(w[0], "grc") for w in words]
    i, hit = 0, False
    for seg in re.split(r"…|\.\.\.", nfc(original)):
        toks = match_key(seg, "grc").split()
        if not toks:
            continue
        for j in range(i, len(keys) - len(toks) + 1):
            if keys[j:j + len(toks)] == toks:
                hit = hit or any(words[k][1] == "bracketed" for k in range(j, j + len(toks)))
                i = j + len(toks)
                break
    return hit


LIST_SEP = re.compile("[,;/\u00b7\u037e\u0387]")


def note_blocks(lines):
    """Split Notes lines into bullets/paragraphs: a blank line or a new list marker starts a block."""
    blocks, cur = [], []
    for l in lines:
        if not l.strip():
            blocks.append(cur)
            cur = []
        elif re.match(r"\s*(?:[-*+]|\d+[.)])\s", l) and cur:
            blocks.append(cur)
            cur = [l]
        else:
            cur.append(l)
    blocks.append(cur)
    return ["\n".join(b) for b in blocks if b]


def ext_note_ok(q, hay_refs, blocks, lines):
    """An editor-bracket note counts only on the quote's own line (inline quote) or in a Notes bullet naming its ref."""
    if q["labels"] is None and EDITOR_NOTE.search(lines[q["line"] - 1]):
        return True
    pats = [re.compile(r"(?<![\w.])" + re.escape(r) + r"(?![\w]|\.\d)") for r in hay_refs]
    return any(EDITOR_NOTE.search(b) and any(p.search(b) for p in pats) for b in blocks)


def inline_quotes(lines, start, block_quotes):
    """Original-language runs outside blockquotes -> (inline quotes, problems).

    A run preceded on its line by `[CORPUS[:WITNESS] Ref]` is an inline quote (verified like a block quote);
    an untagged run of 2+ words is a problem unless it appears verbatim in a quote above it."""
    out, problems, warns = [], [], []
    block_n = 0  # untagged original-language pieces in the current paragraph/bullet (any separator)
    for i in range(start, len(lines)):
        if lines[i].lstrip().startswith(">") or not lines[i].strip() or re.match(r"\s*(?:[-*+]|\d+[.)]|#+)\s", lines[i]):
            block_n = 0
        if lines[i].lstrip().startswith(">"):
            continue
        text = nfc(lines[i])
        code = [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`", text)]  # command snippets do not count toward the cap
        groups, in_code, prev_end = [], set(), None  # untagged runs; runs joined only by a `/` form one list
        for m in SCRIPT_RUN.finditer(text):
            t = INLINE_TAG.search(text[:m.start()])
            if t:
                out.append({"line": i + 1, "tag": t.groups(), "original": m.group(0), "labels": None})
                prev_end = None
                continue
            gap = text[prev_end:m.start()] if prev_end is not None else ""
            if groups and prev_end is not None and "/" in gap and re.fullmatch(r"[\s,;/\u00b7]+", gap):
                groups[-1].append(m.group(0))
            else:
                groups.append([m.group(0)])
            if any(a <= m.start() < b for a, b in code):
                in_code.add(len(groups) - 1)
            prev_end = m.end()
        for gi, g in enumerate(groups):  # untagged: pieces split on , ; / \u00b7 are judged alone (a lemma list is not a quote)
            pieces = [x for run in g for x in LIST_SEP.split(run) if SCRIPT_TOKEN.search(x)]
            for piece in pieces:
                if len(SCRIPT_TOKEN.findall(piece)) >= 2 and not quoted_already(piece, block_quotes + out, i + 1):
                    problems.append((i + 1, "untagged original-language text: tag it inline "
                                            "`[CORPUS[:WITNESS] Ref] <original>` right before the words, or quote it"))
                    break
            else:
                before, block_n = block_n, block_n + (0 if gi in in_code else len(pieces))
                if before < 5 <= block_n:
                    warns.append((i + 1, f"{block_n} separated original-language words in one run \u2014 tag it "
                                         "as a quote if it is text, or keep lemma lists short"))
    return out, list(dict.fromkeys(problems)), warns


def check(path, conn, quotes_only=False, lang=None):
    path = Path(path)
    lines = path.read_text(encoding="utf-8").lstrip("\ufeff").splitlines()
    out = []
    if quotes_only:  # a chat answer: any `---` block is plain text; no --lang: scan with the es and en lists
        body_start, has_fm, terminated = 0, False, True
        fm_lang_given = bool(lang)
        fm = {"language": lang or "en"}
    else:
        body_start, has_fm, terminated = split_frontmatter(lines)
        fm = references.frontmatter(path) if has_fm else {}
        fm_lang_given = bool(lang or fm.get("language"))
        if not terminated:
            out.append(Finding("ERROR", 1, "unterminated frontmatter: close it with a `---` line"))
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
    if quotes_only and not fm_lang_given:
        trad_langs = CHECKED_LANGS
    elif lang and references.tradition_terms(lang):
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

    # quotes: tagged blockquotes, then inline-tagged runs and untagged runs anywhere in the body
    quotes, problems = parse_quotes(lines, body_start)
    inline, run_problems, run_warns = inline_quotes(lines, body_start, quotes)
    out += [Finding("ERROR", ln, msg) for ln, msg in problems + run_problems]
    out += [Finding("WARN", ln, msg) for ln, msg in run_warns]
    blocks = note_blocks(lines if quotes_only else notes_lines)
    for q in quotes + inline:
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
                        if not msg:
                            out += order_findings(conn, corpus, canon, hay_refs, q["line"])
                        if corpus == "ext" and not msg and ext_bracketed(conn, canon, hay_refs, q["original"]):
                            if ext_note_ok(q, hay_refs, blocks, lines):
                                out.append(Finding("WARN", q["line"], "EXT quote includes editor-bracketed words "
                                                   "(the edition marks them as doubtful); keep that visible to the hearer"))
                            else:
                                out.append(Finding("ERROR", q["line"], "EXT quote includes editor-bracketed words "
                                                   "(the edition marks them as doubtful): say so in Notes "
                                                   f"(bracket / corchetes / editor) in the same bullet as the ref (write it as `{hay_refs[0]}`)"))
                        if corpus != "ext" and not quotes_only:
                            hit = (set(hay_refs) | named) & contested
                            miss = sorted(hit - notes_verses)
                            if miss:
                                out.append(Finding("WARN", q["line"],
                                                   f"contested reading {', '.join(miss)} quoted without a mention in Notes"))
        if q["labels"] is None:  # inline quote: no Literal:/Natural: lines
            continue
        for label in ("literal", "natural"):
            if label not in q["labels"]:
                out.append(Finding("ERROR", q["line"], f"missing {label.capitalize()}: line after quote"))
    for q in quotes:
        for label, entries in q["labels"].items():
            for ln, text in entries:
                for m in (trad.finditer(nfc(text)) if trad else ()):
                    out.append(Finding("ERROR", ln, f"tradition term {m.group(0)!r}{trad_src} on {label.capitalize()}: line; use a plain rendering (discuss the term in prose or Notes)"))

    if quotes_only and not quotes and not inline:
        out.append(Finding("ERROR", 1, "no tagged quotes found: --quotes-only checks the tagged quotes of a chat "
                                       "answer (`> [CORPUS Ref] original` or inline `[CORPUS Ref] original`)"))

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
        if findings and len(a.files) > 1:
            print(f"{f}:")
        for x in findings:
            print(f"{x.level} {x.line}: {x.msg}")
        errs = any(x.level == "ERROR" for x in findings)
        if not errs:
            print(f"OK {f}")
        bad = bad or errs
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
