#!/usr/bin/env python3
"""Query CLI for the original-text-sermons skill. Reads data/bible.db (see otslib/db.py).

JSON on stdout by default (--format text for a compact rendering). Errors go to stderr:
exit 1 = unknown ref/witness, exit 2 = bible.db missing.
"""
import argparse
import difflib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from otslib import db  # noqa: E402
from otslib.norm import match_key, nfc, strip_accents  # noqa: E402
from otslib.refs import BOOKS, RefError, canonical, parse_ref, source_ref, to_osis  # noqa: E402

NT = set(BOOKS[BOOKS.index("Matt"):])
CORPORA = ("grnt", "hebot", "lxx", "dss", "ext")
DEFAULT_WITNESS = {"grnt": "SBL", "hebot": "WLC", "lxx": "Rahlfs"}
# DB witness name -> token in TAGNT `editions`
EDITION_TOKEN = {"SBL": "SBL", "NA": "NA28", "THGNT": "Tyn", "WH": "WH", "Byz": "Byz", "TR": "TR"}
WITNESS_ORDER = ["SBL", "NA", "THGNT", "WH", "Byz", "TR", "WLC", "Ketiv", "Rahlfs", "RahlfsA", "RahlfsTh"]
WORD_COLS = ("pos", "surface", "lemma", "strongs", "morph", "gloss", "domain", "syntax_role")
STRONGS_RE = re.compile(r"^([GH])0*(\d+)([A-Za-z]?)$")
EDITIONS = {"NA28", "NA27", "Tyn", "SBL", "WH", "Treg", "TR", "Byz"}
DSS_NOTE = ("dss text holds extant letters only; letters in [brackets] inside word surfaces are "
            "editor-reconstructed, not on the scroll")
OCR_LABEL = "OCR of a printed lexicon (noisy, unverified) - do not quote as verified text"
ENDPUNCT = ".,;·:׃׀()[]“”\"'’"


class Fail(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- helpers

def ref_list(conn, corpus, ref_text):
    """Parse text -> (label, [osis verse refs present in `corpus` in any witness])."""
    if corpus == "ext":  # raw Work.B.S refs are not Bible books (controller ruling 3)
        refs = [ref_text.strip()]
        label = refs[0]
    else:
        try:
            r = parse_ref(ref_text)
        except RefError:
            raise Fail(f"unknown ref: {ref_text}")
        label = to_osis(r)
        if r.verse is None:
            rows = conn.execute("SELECT DISTINCT ref FROM verses WHERE corpus=? AND ref LIKE ?",
                                (corpus, f"{r.book}.{r.chapter}.%")).fetchall()
            refs = sorted((x[0] for x in rows), key=lambda s: int(s.rsplit(".", 1)[1]))
        else:
            refs = [f"{r.book}.{r.chapter}.{v}" for v in range(r.verse, (r.verse_end or r.verse) + 1)]
    have = set()
    for i in range(0, len(refs), 500):
        chunk = refs[i:i + 500]
        q = ",".join("?" * len(chunk))
        have |= {x[0] for x in conn.execute(
            f"SELECT DISTINCT ref FROM verses WHERE corpus=? AND ref IN ({q})", (corpus, *chunk))}
    if not have:
        raise Fail(f"unknown ref: {ref_text}")
    return label, [r for r in refs if r in have]


def default_corpus(ref_text):
    try:
        return "grnt" if parse_ref(ref_text).book in NT else "hebot"
    except RefError:
        raise Fail(f"unknown ref: {ref_text}")


def resolve_witness(conn, corpus, w):
    names = [r[0] for r in conn.execute("SELECT DISTINCT witness FROM verses WHERE corpus=?", (corpus,))]
    for n in names:
        if n.casefold() == w.casefold():
            return n
    raise Fail(f"unknown witness {w!r} for corpus {corpus}; known: {', '.join(sorted(names)[:30])}")


def witnesses_for(conn, corpus, refs):
    q = ",".join("?" * len(refs))
    names = [r[0] for r in conn.execute(
        f"SELECT DISTINCT witness FROM verses WHERE corpus=? AND ref IN ({q})", (corpus, *refs))]
    key = lambda n: (WITNESS_ORDER.index(n) if n in WITNESS_ORDER else 99, n)
    return sorted(names, key=key)


def edition_tokens(editions):
    return {re.split("[»«]", t)[0] for t in (editions or "").split("+") if t}


def is_late(editions):
    """Controller ruling: ignore non-edition tokens (KJV, NIV...); if no edition token remains,
    late only when the original tokens were within {TR, Byz, KJV}."""
    toks = edition_tokens(editions)
    eds = toks & EDITIONS
    if eds:
        return eds <= {"TR", "Byz"}
    return bool(toks) and toks <= {"TR", "Byz", "KJV"}


def verse_words(conn, corpus, witness, ref):
    """Words of one verse for one witness (grnt: TAGNT rows whose editions include the witness)."""
    if corpus == "grnt":
        tok = EDITION_TOKEN.get(witness)
        rows = conn.execute("SELECT * FROM words WHERE corpus='grnt' AND ref=? ORDER BY pos, rowid", (ref,)).fetchall()
        rows = [dict(r) for r in rows if tok in edition_tokens(r["editions"])]
        have = {(r["pos"], r["surface"]) for r in rows}
        # substituted readings live only in `variants` (surface only, no lemma/morph)
        for v in conn.execute("SELECT pos, reading, editions FROM variants WHERE ref=?", (ref,)):
            if tok in edition_tokens(v["editions"]) and (v["pos"], v["reading"]) not in have:
                rows.append({"pos": v["pos"], "surface": v["reading"], "lemma": "", "strongs": "", "morph": "",
                             "gloss": "", "domain": "", "syntax_role": "", "editions": v["editions"],
                             "from_variant": True})
        return sorted(rows, key=lambda r: r["pos"])
    return conn.execute("SELECT * FROM words WHERE corpus=? AND witness=? AND ref=? ORDER BY pos, rowid",
                        (corpus, witness, ref)).fetchall()


def word_dict(row, corpus):
    d = {k: row[k] for k in WORD_COLS}
    if isinstance(row, dict) and row.get("from_variant"):
        d["from_variant"] = True
    if corpus == "dss":
        d["flags"] = [f for f in row["editions"].split(",") if f]
    if corpus == "ext" and row["editions"] == "bracketed":
        d["editor_bracketed"] = True
    return d


def verse_texts(conn, corpus, witness, refs):
    out = {}
    for ref in refs:
        row = conn.execute("SELECT text FROM verses WHERE corpus=? AND witness=? AND ref=?",
                           (corpus, witness, ref)).fetchone()
        if row:
            out[ref] = row[0]
    return out


def is_strongs(q):
    return all(STRONGS_RE.match(t.strip().upper()) for t in q.split("+") if t.strip()) and bool(q.strip())


def strongs_rows(conn, q):
    """Lexicon rows for Strong's number(s). `G1473+G2532` = union; `G2424I` = that exact entry;
    bare `G2010` = G2010 plus its letter-suffixed extensions (never G20100-style longer numbers)."""
    rows = []
    for tok in q.split("+"):
        m = STRONGS_RE.match(tok.strip().upper())
        if not m:
            continue
        n = int(m.group(2))
        base = f"{m.group(1)}{n:04d}" if n < 10000 else f"{m.group(1)}{n}"
        if m.group(3):
            rows += conn.execute("SELECT * FROM lexicon WHERE strongs=?", (base + m.group(3),)).fetchall()
        else:
            rows += conn.execute("SELECT * FROM lexicon WHERE strongs=? OR strongs GLOB ?",
                                 (base, base + "[A-Z]")).fetchall()
    return rows


def lemmas_for(conn, q):
    """lemma, or Strong's number -> the lemma(s) the lexicon gives it."""
    q = nfc(q.strip())
    if not is_strongs(q):
        return [q]
    return sorted({r["lemma"] for r in strongs_rows(conn, q)})


def in_clause(vals):
    return ",".join("?" * len(vals))


def snippet(text, surface, width=5):
    toks = text.split()
    target = strip_accents(surface).casefold().strip(ENDPUNCT)
    for i, t in enumerate(toks):
        if strip_accents(t).casefold().strip(ENDPUNCT) == target:
            lo, hi = max(0, i - width), i + width + 1
            return ("… " if lo else "") + " ".join(toks[lo:hi]) + (" …" if hi < len(toks) else "")
    return text if len(text) <= 100 else text[:100] + " …"


# ---------------------------------------------------------------- commands

def cmd_verse(conn, a, gloss_only=False):
    corpus = a.corpus or default_corpus(a.ref)
    witness = a.witness or DEFAULT_WITNESS.get(corpus)
    if witness is None:
        known = [r[0] for r in conn.execute("SELECT DISTINCT witness FROM verses WHERE corpus=? ORDER BY 1", (corpus,))]
        raise Fail(f"--witness is required for corpus {corpus}; known: {', '.join(known[:30])}")
    label, refs = ref_list(conn, corpus, a.ref)
    witness = resolve_witness(conn, corpus, witness)
    texts = verse_texts(conn, corpus, witness, refs)
    if not texts:
        return {"ref": label, "corpus": corpus, "absent_in": witness,
                "present_in": witnesses_for(conn, corpus, refs)}
    multi = len(refs) > 1
    words = []
    for ref in refs:
        for r in verse_words(conn, corpus, witness, ref) if ref in texts else []:
            d = word_dict(r, corpus)
            if multi:
                d = {"ref": ref, **d}
            words.append(d)
    if gloss_only:
        words = [{k: w[k] for k in ("ref", "pos", "surface", "gloss") if k in w} for w in words]
    out = {"ref": label, "corpus": corpus, "witness": witness, "text": " ".join(texts.values()), "words": words}
    if multi and len(texts) < len(refs):
        out["absent_verses"] = [r for r in refs if r not in texts]
    if corpus in ("grnt", "hebot", "lxx"):
        ntok = sum(len(t.split()) for t in texts.values())
        if not words or len(words) < 0.8 * ntok:
            out["words_note"] = "word-level data incomplete for this witness; text is authoritative"
    if corpus == "dss":
        out["extant_only"] = True
        out["note"] = DSS_NOTE
    if corpus == "ext" and any(w.get("editor_bracketed") for w in words):
        out["editor_bracketed"] = True
    return out


def cmd_interlinear(conn, a):
    a.corpus = a.witness = None
    return cmd_verse(conn, a, gloss_only=True)


def cmd_variants(conn, a):
    label, refs = ref_list(conn, "grnt", a.ref)
    q = in_clause(refs)
    rows = conn.execute(f"SELECT ref, pos, reading, editions FROM variants WHERE ref IN ({q}) ORDER BY rowid", refs)
    out = []
    for r in rows:
        late = is_late(r["editions"])
        out.append({"ref": r["ref"], "pos": r["pos"], "reading": r["reading"], "editions": r["editions"],
                    "class": "late" if late else "early"})
    return out


def cmd_word(conn, a):
    q = nfc(a.query.strip())
    if is_strongs(q):
        lex = [dict(r) for r in strongs_rows(conn, q)]
    else:
        lex = [dict(r) for r in conn.execute("SELECT * FROM lexicon WHERE lemma=?", (q,))]
        if not lex:
            key = strip_accents(q).casefold()
            lex = [dict(r) for r in conn.execute("SELECT * FROM lexicon") if strip_accents(r["lemma"]).casefold() == key]
    lemmas = sorted({r["lemma"] for r in lex}) or [q]
    ph = in_clause(lemmas)

    def n(corpus, wit):
        return conn.execute(f"SELECT COUNT(*) FROM words WHERE corpus=? AND witness=? AND lemma IN ({ph})",
                            (corpus, wit, *lemmas)).fetchone()[0]

    def doms(corpus):
        return [r[0] for r in conn.execute(
            f"SELECT domain FROM words WHERE corpus=? AND lemma IN ({ph}) AND domain!='' "
            "GROUP BY domain ORDER BY COUNT(*) DESC, domain LIMIT 20", (corpus, *lemmas))]

    # ponytail: same-verse co-occurrence, not true alignment - a Hebrew lemma listed here is merely
    # in a verse where the LXX uses this Greek lemma; verify by reading both verses.
    co = [{"lemma": r[0], "verses": r[1]} for r in conn.execute(
        f"""SELECT h.lemma, COUNT(DISTINCT h.ref) c FROM words l
            JOIN words h ON h.corpus='hebot' AND h.witness='WLC' AND h.ref=l.ref
            WHERE l.corpus='lxx' AND l.witness='Rahlfs' AND l.lemma IN ({ph}) AND h.lemma!=''
            GROUP BY h.lemma ORDER BY c DESC, h.lemma LIMIT 10""", lemmas)]
    return {"query": a.query, "lexicon": lex,
            "domains": {"louw_nida": doms("grnt"), "sdbh": doms("hebot")},
            "counts": {"nt": n("grnt", "TAGNT"), "lxx": n("lxx", "Rahlfs"), "hebot": n("hebot", "WLC")},
            "lxx_hebrew_cooccurrence": co,
            "lxx_hebrew_cooccurrence_note": "same-verse co-occurrence, not alignment"}


def cmd_usage(conn, a):
    lemma = nfc(a.lemma.strip())
    counts, ctx = {}, {}
    for corpus, wit in (("grnt", "TAGNT"), ("lxx", "Rahlfs")):
        rows = conn.execute("SELECT ref, surface FROM words WHERE corpus=? AND witness=? AND lemma=? ORDER BY rowid",
                            (corpus, wit, lemma)).fetchall()
        counts[corpus] = len(rows)
        vw = "SBL" if corpus == "grnt" else wit
        ctx[corpus] = []
        for r in rows[:5]:
            t = conn.execute("SELECT text FROM verses WHERE corpus=? AND witness=? AND ref=?",
                             (corpus, vw, r["ref"])).fetchone()
            ctx[corpus].append({"ref": r["ref"], "snippet": snippet(t[0], r["surface"]) if t else r["surface"]})
    # ponytail: ext has no lemmas, so we match accent-stripped surface forms seen for this lemma in
    # grnt+lxx; ceiling = homograph forms of other lemmas inflate counts, and forms never seen in
    # grnt/lxx are missed.
    forms = {strip_accents(s).casefold() for (s,) in conn.execute(
        "SELECT DISTINCT surface FROM words WHERE corpus IN ('grnt','lxx') AND lemma=?", (lemma,))}
    forms.discard("")
    conn.create_function("ots_key", 1, lambda s: strip_accents(s or "").casefold().strip(ENDPUNCT))
    ext = conn.execute(
        f"SELECT witness, ref, surface, editions FROM words WHERE corpus='ext' AND ots_key(surface) IN ({in_clause(forms)}) "
        "ORDER BY rowid", tuple(forms)).fetchall() if forms else []
    counts["ext"] = len(ext)
    ctx["ext"] = []
    for r in ext[:5]:
        t = conn.execute("SELECT text FROM verses WHERE corpus='ext' AND witness=? AND ref=?",
                         (r["witness"], r["ref"])).fetchone()
        c = {"witness": r["witness"], "ref": r["ref"], "snippet": snippet(t[0], r["surface"]) if t else r["surface"]}
        if r["editions"] == "bracketed":
            c["editor_bracketed"] = True
        ctx["ext"].append(c)
    pap = [{"lemma": r["lemma"], "entry": r["entry"], "label": OCR_LABEL}
           for r in conn.execute("SELECT lemma, entry FROM papyri_vocab WHERE lemma=? OR lemma=?",
                                 (lemma, unicodedata.normalize("NFD", lemma)))]
    qual = conn.execute("SELECT value FROM meta WHERE key='papyri_quality'").fetchone()
    return {"lemma": lemma, "counts": counts, "contexts": ctx, "lxx_witness": "Rahlfs",
            "papyri": pap or None, "papyri_quality": qual[0] if qual else "unknown"}


def cmd_compare(conn, a):
    corpus = default_corpus(a.ref)
    label, refs = ref_list(conn, corpus, a.ref)
    wit = DEFAULT_WITNESS[corpus]
    orig = verse_texts(conn, corpus, wit, refs)
    avail = [r[0] for r in conn.execute("SELECT DISTINCT version FROM translations ORDER BY version")]
    if a.versions:
        want = []
        for v in (x.strip() for x in a.versions.split(",") if x.strip()):
            hit = next((n for n in avail if n.casefold() == v.casefold()), None)
            if hit is None:
                raise Fail(f"unknown version {v!r}; available: {', '.join(avail)}")
            want.append(hit)
    else:
        want = avail
    versions = {}
    for v in want:
        q = in_clause(refs)
        rows = dict(conn.execute(f"SELECT ref, text FROM translations WHERE version=? AND ref IN ({q})", (v, *refs)).fetchall())
        if rows:
            versions[v] = " ".join(rows[r] for r in refs if r in rows)
    return {"ref": label, "original": " ".join(orig.values()), "original_corpus": corpus,
            "original_witness": wit, "versions": versions}


_NIQQUD = re.compile("[֑-ׇ]")


def cons(s):
    """Hebrew consonantal skeleton, tokens split on spaces and maqaf."""
    return _NIQQUD.sub("", s.replace("־", " ")).split()


def diff_ops(a_tokens, b_tokens, key="base"):
    ops = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_tokens, b_tokens, autojunk=False).get_opcodes():
        if tag != "equal":
            ops.append({"op": tag, key: a_tokens[i1:i2], "reading": b_tokens[j1:j2]})
    return ops


def hebot_text(conn, refs):
    rows = verse_texts(conn, "hebot", "WLC", refs)
    return " ".join(rows.values())


def cmd_dss(conn, a):
    label, refs = ref_list(conn, "dss", a.ref)
    heb = hebot_text(conn, refs)
    heb_t = cons(heb)
    readings = []
    for w in witnesses_for(conn, "dss", refs):
        text = " ".join(verse_texts(conn, "dss", w, refs).values())
        toks = cons(text)
        ops = diff_ops(heb_t, toks)
        flags = sorted({f for r in conn.execute(
            f"SELECT editions FROM words WHERE corpus='dss' AND witness=? AND ref IN ({in_clause(refs)})", (w, *refs))
            for f in r[0].split(",") if f})
        readings.append({"witness": w, "text": text, "extant_only": True, "flags": flags,
                         "tokens": len(toks), "hebot_tokens": len(heb_t), "identical_to_wlc": not ops,
                         "diff_vs_hebot": ops})
    return {"ref": label, "base_witness": "WLC", "note": DSS_NOTE + "; diff tokens are consonant-only skeletons (WLC vowels/accents stripped); diff compares consonants only (WLC vowels/accents stripped); "
            "'delete' ops are WLC words not extant in the fragment (lacuna or omission - judge from the scroll's extent)",
            "hebot_wlc": heb, "readings": readings}


def cmd_lxx(conn, a):
    label, refs = ref_list(conn, "lxx", a.ref)
    heb = hebot_text(conn, refs)
    ws = witnesses_for(conn, "lxx", refs)
    texts = {w: " ".join(verse_texts(conn, "lxx", w, refs).values()) for w in ws}
    base = texts.get("Rahlfs") or next(iter(texts.values()))
    base_t = [match_key(t, "grc") for t in base.split()]
    readings = []
    for w in ws:
        toks = [match_key(t, "grc") for t in texts[w].split()]
        r = {"witness": w, "text": texts[w], "tokens": len(toks), "hebot_tokens": len(cons(heb))}
        if w != "Rahlfs" and "Rahlfs" in texts:
            r["diff_vs_rahlfs"] = diff_ops(base_t, toks)
        readings.append(r)
    # Greek and Hebrew tokens are not comparable form-by-form, so the word-level diff is run between
    # LXX witnesses; the Hebrew text and token counts are given for plus/minus-sized differences.
    first = refs[0]
    return {"ref": label, "lxx_ref": source_ref(conn, "lxx", first) if len(refs) == 1 else None,
            "hebrew_ref": source_ref(conn, "hebrew", first) if len(refs) == 1 else None,
            "base_witness": "Rahlfs",
            "note": "Greek vs Hebrew tokens are not diffed (different languages); witnesses are diffed against Rahlfs "
                    "(`base` = Rahlfs tokens); diff tokens are match_key forms (normalised, casefolded, not display text); "
                    "WLC text and token counts are given for comparison",
            "hebot_wlc": heb, "readings": readings}


def cmd_search(conn, a):
    lemmas = lemmas_for(conn, a.query)
    corpora = [a.corpus] if a.corpus else ["grnt", "lxx", "hebot"]
    wit = {"grnt": "TAGNT", "lxx": "Rahlfs", "hebot": "WLC"}
    res = {}
    for c in corpora:
        sql = "SELECT ref, COUNT(*) FROM words WHERE corpus=? AND lemma IN (%s)" % in_clause(lemmas)
        args = [c, *lemmas]
        if c in wit:
            sql += " AND witness=?"
            args.append(wit[c])
        rows = conn.execute(sql + " GROUP BY witness, ref ORDER BY MIN(rowid)", args).fetchall()
        refs = [r[0] for r in rows]
        res[c] = {"verses": len(refs), "occurrences": sum(r[1] for r in rows), "refs": refs[:a.limit],
                  "truncated": len(refs) > a.limit}
    return {"query": a.query, "lemmas": lemmas, "results": res}


# ---------------------------------------------------------------- text rendering

def render_text(cmd, out):
    L = []
    if cmd in ("verse", "interlinear"):
        if "absent_in" in out:
            return f"{out['ref']} [{out['corpus']}]: absent in {out['absent_in']}; present in {', '.join(out['present_in'])}"
        L.append(f"{out['ref']} [{out['corpus']}:{out['witness']}]  {out['text']}")
        if out.get("note"):
            L.append(f"  note: {out['note']}")
        for w in out["words"]:
            parts = [str(w.get("ref", "")) if "ref" in w else "", str(w["pos"]), w["surface"]]
            if cmd == "verse":
                parts += [w["lemma"], w["strongs"], w["morph"], w["gloss"]]
                if w.get("flags"):
                    parts.append("flags=" + ",".join(w["flags"]))
                if w.get("editor_bracketed"):
                    parts.append("[editor-bracketed]")
            else:
                parts.append(w["gloss"])
            L.append("  " + " | ".join(p for p in parts if p != ""))
    elif cmd == "variants":
        for v in out:
            L.append(f"{v['ref']} #{v['pos']} {v['reading']}  [{v['editions']}]  {v['class']}")
    elif cmd == "word":
        for r in out["lexicon"]:
            L.append(f"{r['strongs']} {r['lemma']} ({r['lang']}): {r['gloss']}")
        L.append(f"counts: {out['counts']}")
        L.append(f"domains: {out['domains']}")
        L.append("LXX/Hebrew same-verse co-occurrence (not alignment): " +
                 ", ".join(f"{c['lemma']}({c['verses']})" for c in out["lxx_hebrew_cooccurrence"]))
    elif cmd == "usage":
        L.append(f"{out['lemma']}: {out['counts']}")
        for c, items in out["contexts"].items():
            for i in items:
                L.append(f"  {c} {i['ref']}: {i['snippet']}" + (" [editor-bracketed]" if i.get("editor_bracketed") else ""))
        if out["papyri"]:
            for p in out["papyri"]:
                L.append(f"papyri ({out['papyri_quality']}; {p['label']}): {p['entry'][:300]}")
        else:
            L.append("papyri: none")
    elif cmd == "compare":
        L.append(f"{out['ref']} {out['original_witness']}: {out['original']}")
        for v, t in out["versions"].items():
            L.append(f"  {v}: {t}")
    elif cmd in ("dss", "lxx"):
        L.append(f"{out['ref']}  WLC: {out['hebot_wlc']}")
        L.append(f"note: {out['note']}")
        for r in out["readings"]:
            L.append(f"  {r['witness']}: {r['text']}")
            for d in r.get("diff_vs_hebot", r.get("diff_vs_rahlfs", [])):
                L.append(f"    {d['op']}: {' '.join(d['base'])} -> {' '.join(d['reading'])}")
    elif cmd == "search":
        for c, r in out["results"].items():
            L.append(f"{c}: {r['occurrences']} in {r['verses']} verses: {', '.join(r['refs'])}" + (" ..." if r["truncated"] else ""))
    return "\n".join(L)


# ---------------------------------------------------------------- main

def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=("json", "text"), default=argparse.SUPPRESS)
    common.add_argument("--db", default=argparse.SUPPRESS, help="path to bible.db (default: $OTS_DB or data/bible.db)")
    ap = argparse.ArgumentParser(description=__doc__, parents=[common])
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        p = sub.add_parser(name, parents=[common], **kw)
        p.set_defaults(fn=fn)
        return p

    p = add("verse", cmd_verse, help="original text + words")
    p.add_argument("ref")
    p.add_argument("--corpus", choices=CORPORA)
    p.add_argument("--witness")
    add("interlinear", cmd_interlinear, help="surface + gloss per word").add_argument("ref")
    add("variants", cmd_variants, help="NT edition variants").add_argument("ref")
    add("word", cmd_word, help="lexicon, domains, counts").add_argument("query", help="lemma or Strong's number")
    add("usage", cmd_usage, help="1st-century usage evidence").add_argument("lemma")
    p = add("compare", cmd_compare, help="original vs translations")
    p.add_argument("ref")
    p.add_argument("--versions", help="comma-separated, e.g. KJV,BSB")
    add("dss", cmd_dss, help="Dead Sea Scroll readings vs WLC").add_argument("ref")
    add("lxx", cmd_lxx, help="LXX readings").add_argument("ref")
    p = add("search", cmd_search, help="refs where a lemma occurs")
    p.add_argument("query", help="lemma or Strong's number")
    p.add_argument("--corpus", choices=("grnt", "hebot", "lxx", "dss"))
    p.add_argument("--limit", type=int, default=200)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    if getattr(a, "db", None):
        os.environ["OTS_DB"] = a.db
    conn = db.require_db()
    try:
        out = a.fn(conn, a)
    except Fail as e:
        print(str(e), file=sys.stderr)
        return e.code
    if getattr(a, "format", "json") == "text":
        print(render_text(a.cmd, out))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
