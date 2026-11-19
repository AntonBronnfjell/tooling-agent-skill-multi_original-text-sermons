import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

from test_build_stepbible import FIXTURES  # noqa: E402
import build_db  # noqa: E402
import check_sermon  # noqa: E402
from check_sermon import check  # noqa: E402
from otslib import db  # noqa: E402

FX = ROOT / "evals" / "fixtures"
POS = sorted((FX / "positive").glob("*.md"))
CHECK = ROOT / "scripts" / "check_sermon.py"

J11 = ("> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος\n> Literal: and god was the word\n"
       "> Natural: and the word was God\n")


def fm(**kw):
    d = dict(passage="John.1.1", language="en", specialization="theology", audience="church",
             template="big-idea", date="2026-11-18")
    d.update(kw)
    d = {k: v for k, v in d.items() if v is not None}
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in d.items()) + "---\n\n"


EN = ["Introduction", "Text", "Big Idea", "Point 1", "Point 2", "Point 3", "Conclusion", "Notes"]
ES = ["Introducción", "Texto", "Idea central", "Punto 1", "Punto 2", "Punto 3", "Conclusión", "Notas"]


def body(heads=EN, quote=J11, notes="- John.1.1 options.", prose="prose"):
    out = ""
    for h in heads:
        out += f"## {h}\n\n"
        if h in (heads[1],):
            out += f"{prose}\n\n{quote}\n"
        elif h == heads[-1]:
            out += notes + "\n"
        else:
            out += "text\n\n"
    return out


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.dbfile = os.path.join(cls.tmp, "t.db")
        build_db.build(Path(FIXTURES), Path(cls.dbfile), out=io.StringIO())
        cls.conn = db.connect(cls.dbfile)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        import shutil
        shutil.rmtree(cls.tmp)

    def run_text(self, text):
        p = Path(self.tmp) / "s.md"
        p.write_text(text, encoding="utf-8")
        return check(p, self.conn)

    def msgs(self, rel):
        return " | ".join(f.msg for f in check(FX / rel, self.conn))

    def errors(self, rel):
        return [f for f in check(FX / rel, self.conn) if f.level == "ERROR"]

    def warns(self, rel):
        return " | ".join(f.msg for f in check(FX / rel, self.conn) if f.level == "WARN")


class Fixtures(Base):
    def test_positive_fixtures_pass(self):
        self.assertTrue(POS)
        for f in POS:
            self.assertFalse([x for x in check(f, self.conn) if x.level == "ERROR"], f)

    def test_misquote(self): self.assertIn("not found", self.msgs("negative/misquote.md"))
    def test_tr_as_default(self): self.assertIn("not found", self.msgs("negative/comma-as-sbl.md"))
    def test_tr_tagged_ok(self): self.assertNotIn("not found", self.msgs("positive/comma-tagged-tr.md"))
    def test_dss_requires_witness(self): self.assertIn("requires a witness", self.msgs("negative/dss-no-witness.md"))
    def test_tradition_term_on_natural(self): self.assertIn("tradition term", self.msgs("negative/church-in-natural.md"))
    def test_tradition_term_in_prose_ok(self): self.assertNotIn("tradition term", self.msgs("positive/church-in-prose.md"))
    def test_ellipsis_and_range(self): self.assertFalse(self.errors("positive/ellipsis-range.md"))
    def test_missing_section(self): self.assertIn("missing section", self.msgs("negative/no-conclusion.md"))
    def test_contested_without_note_warns(self): self.assertIn("contested", self.warns("negative/john-1-1-no-note.md"))
    def test_contested_with_note_ok(self): self.assertNotIn("contested", self.warns("positive/john-1-1-with-note.md"))
    def test_greek_accents_must_match(self): self.assertIn("not found", self.msgs("negative/accent-dropped.md"))
    @unittest.skipUnless((ROOT / "data" / "bible.db").is_file(), "real bible.db not built")
    def test_sermon_output_template_valid(self):
        # the example quotes Judg.11.34 and Josephus Ant.1.222, which the small fixture DB lacks
        conn = db.connect(ROOT / "data" / "bible.db")
        try:
            errs = [f for f in check(ROOT / "templates" / "sermon-output.md", conn) if f.level == "ERROR"]
        finally:
            conn.close()
        self.assertEqual(errs, [])

    def test_exit_codes(self):
        env = {**os.environ, "OTS_DB": self.dbfile}
        ok = subprocess.run([sys.executable, str(CHECK), *map(str, POS)], capture_output=True, text=True, env=env)
        self.assertEqual(ok.returncode, 0, ok.stdout)
        bad = subprocess.run([sys.executable, str(CHECK), str(FX / "negative/misquote.md")], capture_output=True,
                             text=True, env=env)
        self.assertEqual(bad.returncode, 1)
        self.assertRegex(bad.stdout, r"ERROR \d+: ")

    def test_missing_db_exits_2(self):
        env = {**os.environ, "OTS_DB": os.path.join(self.tmp, "nope.db")}
        r = subprocess.run([sys.executable, str(CHECK), str(POS[0])], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("bible.db", r.stderr)


NEG_ERR = {
    "tag-space-after-colon": "unparseable quote tag",
    "tag-bold": "unparseable quote tag",
    "tag-no-space": "unparseable quote tag",
    "tag-parens": "untagged original-language text",
    "untagged-greek-blockquote": "untagged original-language text",
    "greek-after-natural": "untagged original-language text",
    "template-sermon-output": "template",
    "template-traversal": "template",
    "dup-natural-church": "tradition term",
    "natural-continuation-church": "tradition term",
    "range-nonexistent": "not found",
    "range-giant": "range",
    "chapter-only": "chapter",
    "language-unsupported": "invalid language value",
}


class Hardening(Base):
    def test_negative_fixtures_error_with_message(self):
        for name, frag in NEG_ERR.items():
            errs = [f.msg for f in check(FX / "negative" / f"{name}.md", self.conn) if f.level == "ERROR"]
            self.assertTrue(any(frag in m for m in errs), (name, errs))

    def test_language_unsupported_fixture_errors(self):
        errs = [f.msg for f in check(FX / "negative" / "language-unsupported.md", self.conn) if f.level == "ERROR"]
        self.assertTrue(any("invalid language value" in m for m in errs), errs)
        self.assertTrue(any("tradition term 'church' (es/en list)" in m for m in errs), errs)

    def test_portuguese_positive_fixture_warns_only(self):
        fs = check(FX / "positive" / "portuguese-custom.md", self.conn)
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)
        self.assertTrue(any("not checked for pt" in f.msg for f in fs if f.level == "WARN"), fs)
        self.assertFalse(any("contested" in f.msg for f in fs), fs)

    def test_other_language_custom_sections_validates_with_warn(self):
        pt = ["Introdução", "Texto", "Conclusão", "Anotações"]
        quote = J11.replace("and the word was God", "a igreja")  # not checked for pt
        fs = self.run_text(fm(language="pt", template="custom", sections=", ".join(pt))
                           + body(pt, quote=quote, notes="- John.1.1 opções."))
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)
        warns = [f.msg for f in fs if f.level == "WARN"]
        self.assertTrue(any("tradition vocabulary not checked for pt" in m for m in warns), warns)
        # last custom section counts as Notes: John.1.1 is mentioned there, so no contested warning
        self.assertFalse(any("contested" in m for m in warns), warns)

    def test_other_language_quotes_still_verified(self):
        q = "> [GRC John.1.1] καὶ θεὸς ἦν ὁ κόσμος\n> Literal: a\n> Natural: b\n"
        fs = self.run_text(fm(language="pt-BR", template="custom", sections="Texto, Notas") + body(["Texto", "Notas"], quote=q))
        self.assertTrue(any("not found" in f.msg for f in fs if f.level == "ERROR"), fs)

    def test_other_language_named_template_needs_english_headings(self):
        self.assertEqual([f.msg for f in self.run_text(fm(language="pt") + body()) if f.level == "ERROR"], [])
        pt = ["Introdução", "Texto", "Ideia central", "Ponto 1", "Ponto 2", "Ponto 3", "Conclusão", "Notas"]
        errs = [f.msg for f in self.run_text(fm(language="pt") + body(pt)) if f.level == "ERROR"]
        self.assertTrue(any("missing section" in m for m in errs), errs)

    def test_custom_last_section_is_notes(self):
        heads = ["Abertura", "Leitura", "Fontes"]
        miss = self.run_text(fm(language="pt", template="custom", sections=", ".join(heads))
                             + body(heads, notes="- nada"))
        self.assertTrue(any("contested" in f.msg for f in miss if f.level == "WARN"))
        ok = self.run_text(fm(language="pt", template="custom", sections=", ".join(heads))
                           + body(heads, notes="- John.1.1 opções"))
        self.assertFalse(any("contested" in f.msg for f in ok if f.level == "WARN"))

    def custom_with(self, lang, natural):
        quote = J11.replace("and the word was God", natural)
        return self.run_text(fm(language=lang, template="custom", sections="Texto, Notas")
                             + body(["Texto", "Notas"], quote=quote, notes="- John.1.1 opciones."))

    def test_language_value_forms_cannot_bypass_tradition_check(self):
        for lang in ('"es"', "'es'", "es # spanish", "esp", "sp", "pt", "Spanish (es)", "'en'"):
            errs = [f.msg for f in self.custom_with(lang, "la iglesia y the church") if f.level == "ERROR"]
            self.assertTrue(errs, lang)
            self.assertTrue(any("tradition term" in m or "invalid language" in m for m in errs), (lang, errs))

    def test_quoted_and_commented_language_fully_checked(self):
        for lang in ('"es"', "'es'", "es # spanish"):
            fs = self.custom_with(lang, "la iglesia")
            self.assertTrue(any("tradition term 'iglesia'" in f.msg for f in fs if f.level == "ERROR"), (lang, fs))
            self.assertFalse(any("not checked" in f.msg for f in fs), (lang, fs))

    def test_invalid_language_value_errors(self):
        for lang in ("Spanish (es)", "es/en", "español!"):
            errs = [f.msg for f in self.custom_with(lang, "a palavra") if f.level == "ERROR"]
            self.assertTrue(any("invalid language value" in m for m in errs), (lang, errs))

    def test_unknown_code_scans_es_and_en_lists(self):
        for lang, term in (("esp", "iglesia"), ("sp", "church"), ("pt", "bautizar")):
            errs = [f.msg for f in self.custom_with(lang, f"a {term}") if f.level == "ERROR"]
            self.assertTrue(any("tradition term" in m and "es/en list" in m for m in errs), (lang, errs))

    def test_real_portuguese_warns_only(self):
        fs = self.custom_with("pt", "e a palavra era Deus / divina")
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)
        self.assertTrue(any("not checked" in f.msg for f in fs if f.level == "WARN"), fs)

    def test_notes_prefix_in_body_not_taken_as_notes(self):
        # body heading "Notas previas" shares the prefix of the last section "Notas" but comes before it
        heads = ["Notas previas", "Texto", "Notas"]
        t = (fm(language="pt", template="custom", sections="Notas previas, Texto, Notas")
             + "## Notas previas\n\n- John.1.1 aqui não conta\n\n## Texto\n\n" + J11
             + "\n## Notas\n\n- nada\n")
        self.assertTrue(any("contested" in f.msg for f in self.run_text(t) if f.level == "WARN"))
        t2 = t.replace("- John.1.1 aqui não conta", "- x").replace("- nada", "- John.1.1 opções")
        self.assertFalse(any("contested" in f.msg for f in self.run_text(t2) if f.level == "WARN"))

    def test_stitched_single_words_warns(self):
        fs = check(FX / "negative" / "stitched-single-words.md", self.conn)
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)
        self.assertTrue(any("one-word" in f.msg for f in fs if f.level == "WARN"))
        self.assertTrue(any("segments" in f.msg for f in fs if f.level == "WARN"))

    def test_prose_greek_run_errors(self):
        t = fm(template="custom", sections="Text, Notes") + "## Text\n\nκαὶ θεὸς ἦν ὁ λόγος here\n\n## Notes\n\nx\n"
        self.assertTrue(any("untagged original-language text" in f.msg for f in self.run_text(t) if f.level == "ERROR"))
        t = fm(template="custom", sections="Text, Notes") + "## Text\n\nthe word λόγος and ἦν only\n\n## Notes\n\nx\n"
        self.assertFalse(any("original-language words" in f.msg for f in self.run_text(t)))

    def test_language_names_normalized(self):
        for lang in ("Spanish", "español", "es-MX", "ES"):
            e = [f.msg for f in self.run_text(fm(language=lang, template="custom", sections="Text, Notes") + body(["Text", "Notes"], quote=J11.replace("the word was God", "la iglesia")))
                 if f.level == "ERROR"]
            self.assertTrue(any("tradition term" in m for m in e), (lang, e))
        e = [f.msg for f in self.run_text(fm(language="English") + body())]
        self.assertFalse(any("language" in m for m in e))

    def test_template_name_restricted(self):
        for t in ("sermon-output", "../references/tradition-vocabulary", "Big-Idea"):
            self.assertTrue(any("template" in f.msg for f in self.run_text(fm(template=t) + body()) if f.level == "ERROR"), t)

    def test_dss_uses_hebrew_matching(self):
        q = "> [DSS:1QIsaa Isa.53.11] יראה אור וישבע\n> Literal: a\n> Natural: b\n"
        self.assertFalse([f for f in self.run_text(fm(passage="Isa.53.11") + body(quote=q, notes="- Isa.53.11")) if f.level == "ERROR"])

    def test_reversed_range(self):
        q = "> [GRC John.3.17-16] ἀλλ\n> Literal: a\n> Natural: b\n"
        self.assertTrue([f for f in self.run_text(fm() + body(quote=q)) if f.level == "ERROR"])

    def test_non_db_file_exit_2(self):
        bad = os.path.join(self.tmp, "junk.db")
        Path(bad).write_text("not a database at all" * 100)
        r = subprocess.run([sys.executable, str(CHECK), "--db", bad, str(POS[0])], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)
        empty = os.path.join(self.tmp, "empty.db")
        sqlite3.connect(empty).close()
        r = subprocess.run([sys.executable, str(CHECK), "--db", empty, str(POS[0])], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("Traceback", r.stderr)


class Rulings(Base):
    def errs(self, text):
        return [f.msg for f in self.run_text(text) if f.level == "ERROR"]

    def warns_of(self, text):
        return [f.msg for f in self.run_text(text) if f.level == "WARN"]

    def test_valid_minimal(self):
        self.assertEqual(self.errs(fm() + body()), [])

    def test_missing_frontmatter_key(self):
        self.assertTrue(any("frontmatter key: audience" in m for m in self.errs(fm(audience=None) + body())))

    def test_unknown_corpus_witness_ref(self):
        q = lambda tag, ref: f"> [{tag} {ref}] καὶ\n> Literal: a\n> Natural: b\n"
        self.assertTrue(any("unknown corpus" in m for m in self.errs(fm() + body(quote=q("FOO", "John.1.1")))))
        self.assertTrue(any("unknown witness" in m for m in self.errs(fm() + body(quote=q("GRC:ZZZ", "John.1.1")))))
        self.assertTrue(any("unknown ref" in m or "not found" in m for m in self.errs(fm() + body(quote=q("GRC", "Nonsense 1:1")))))

    def test_missing_literal_natural(self):
        e = self.errs(fm() + body(quote="> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος\n"))
        self.assertTrue(any("Literal" in m for m in e) and any("Natural" in m for m in e))

    def test_ellipsis_order_enforced(self):
        q = "> [GRC John.1.1] ὁ λόγος … ἐν ἀρχῇ\n> Literal: a\n> Natural: b\n"
        self.assertTrue(any("not found" in m for m in self.errs(fm() + body(quote=q))))
        q = "> [GRC John.1.1] ἐν ἀρχῇ ... καὶ θεὸς\n> Literal: a\n> Natural: b\n"
        self.assertEqual(self.errs(fm() + body(quote=q)), [])

    def test_partial_word_does_not_match(self):
        q = "> [GRC John.1.1] καὶ θε\n> Literal: a\n> Natural: b\n"
        self.assertTrue(any("not found" in m for m in self.errs(fm() + body(quote=q))))

    def test_hebrew_pointed_unpointed_and_wrong(self):
        mk = lambda t: f"> [HEB Gen.1.1] {t}\n> Literal: a\n> Natural: b\n"
        self.assertEqual(self.errs(fm(passage="Gen.1.1") + body(quote=mk("בְּרֵאשִׁית בָּרָא אֱלֹהִים"))), [])
        self.assertEqual(self.errs(fm(passage="Gen.1.1") + body(quote=mk("בראשית ברא אלהים"))), [])
        self.assertTrue(self.errs(fm(passage="Gen.1.1") + body(quote=mk("בְּרֵאשִׁית בָּרָא אֱלֹהֵים"))))  # wrong vowel

    def test_dss_unpointed_with_witness(self):
        q = "> [DSS:1QIsaa Isa.53.11] יראה אור וישבע\n> Literal: a\n> Natural: b\n"
        self.assertEqual(self.errs(fm(passage="Isa.53.11") + body(quote=q, notes="- Isa.53.11 noted")), [])

    def test_dss_quote_cannot_bridge_lacuna(self):
        mk = lambda t: f"> [DSS:4Q58 Isa.53.11] {t}\n> Literal: a\n> Natural: b\n"
        f = fm(passage="Isa.53.11")
        n = "- Isa.53.11 noted"
        self.assertTrue(any("not found" in m for m in self.errs(f + body(quote=mk("עבדי לר הוא יסבול"), notes=n))))
        self.assertEqual(self.errs(f + body(quote=mk("עבדי לר … הוא יסבול"), notes=n)), [])

    def test_ext_witness_required_and_ok(self):
        q = "> [EXT Ant.18.63] x\n> Literal: a\n> Natural: b\n"
        self.assertTrue(any("requires a witness" in m for m in self.errs(fm() + body(quote=q))))

    def test_headings_localized_or_english(self):
        self.assertEqual(self.errs(fm(language="es") + body(ES, notes="- John.1.1")), [])
        self.assertEqual(self.errs(fm(language="es") + body(EN)), [])
        mixed = ["Introducción", "Text", "Idea central", "Point 1", "Punto 2", "Punto 3", "Conclusion", "Notas"]
        self.assertEqual(self.errs(fm(language="es") + body(mixed)), [])
        self.assertTrue(any("missing section" in m for m in self.errs(fm(language="es") + body(ES[:-2] + ["Notas"]))))

    def test_heading_prefix_case_insensitive(self):
        heads = ["introduction — x", "TEXT", "big idea!", "Point 1 — a", "Point 2: b", "Point 3", "Conclusion", "Notes"]
        self.assertEqual(self.errs(fm() + body(heads)), [])

    def test_custom_template_requires_sections(self):
        e = self.errs(fm(template="custom") + body())
        self.assertTrue(any("custom" in m and "sections" in m for m in e))
        self.assertEqual(self.errs(fm(template="custom", sections="Text, Notes") + body(["Text", "Notes"])), [])
        self.assertTrue(any("missing section" in m for m in self.errs(fm(template="custom", sections="Text, Nope, Notes") + body(["Text", "Notes"]))))

    def test_unknown_template(self):
        self.assertTrue(any("unknown template" in m for m in self.errs(fm(template="zzz") + body())))

    def test_contested_range_expansion_and_human_ref_forms(self):
        john8 = "> [GRC John.8.5] ὁ λόγος\n> Literal: a\n> Natural: b\n"   # inside John.8.1-11; fixture may lack it
        for notes in ("- Juan 1:1 es disputado", "- see Jn 1:1", "- John.1.1 options", "- 1 Juan ignored. John 1:1-2 range"):
            self.assertEqual([m for m in self.warns_of(fm() + body(notes=notes)) if "contested" in m], [], notes)
        w = self.warns_of(fm() + body(notes="- Gen.1.1 only; John.1.2 irrelevant"))
        self.assertTrue(any("contested" in m and "John.1.1" in m for m in w))
        # range entries expand: Mark.16.9-20 contains Mark.16.15
        import check_sermon as cs
        self.assertIn("Mark.16.15", cs.contested_verses())
        self.assertIn("John.8.5", cs.contested_verses())

    def test_notes_section_only_counts(self):
        text = fm() + body(notes="- nothing here").replace("text\n\n## Text", "John.1.1 here\n\n## Text", 1)
        self.assertTrue(any("contested" in m for m in self.warns_of(text)))

    def test_tradition_terms_word_boundaries(self):
        mk = lambda nat: fm() + body(quote=f"> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος\n> Literal: a\n> Natural: {nat}\n")
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("The CHURCH gathered"))))
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("the church's people"))))
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("the church’s people"))))
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("a holy  ghost"))))
        self.assertEqual(self.errs(mk("churchlike sainthood"))[:0], [])
        self.assertFalse(any("tradition term" in m for m in self.errs(mk("churchlike and hellenic"))))

    def test_tradition_terms_spanish_accents(self):
        mk = lambda nat: fm(language="es") + body(ES, quote=f"> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος\n> Literal: {nat}\n> Natural: ok\n")
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("el Apóstol y la Iglesia"))))
        self.assertTrue(any("tradition term" in m for m in self.errs(mk("pecado original"))))
        # accent-bearing neighbours are letters: no match inside a longer word
        self.assertFalse(any("tradition term" in m for m in self.errs(mk("iglesiásmente"))))  # exact-form row
        # English term is not enforced on a Spanish sermon
        self.assertFalse(any("tradition term" in m for m in self.errs(mk("church"))))

    def test_word_count_warning_excludes_quotes_and_notes(self):
        words = lambda n: " ".join(["palabra"] * n)
        long_notes = words(2000)
        ok = fm() + body(prose=words(600), notes=long_notes)
        self.assertFalse([m for m in self.warns_of(ok) if "word count" in m])
        self.assertTrue([m for m in self.warns_of(fm() + body(prose=words(10))) if "word count" in m])
        self.assertTrue([m for m in self.warns_of(fm() + body(prose=words(1400))) if "word count" in m])
        many_quote_words = J11 + "> Natural: " + words(2000) + "\n"
        self.assertFalse([m for m in self.warns_of(fm() + body(prose=words(600), quote=many_quote_words)) if "word count" in m])

    def test_findings_are_namedtuples(self):
        f = self.run_text(fm() + body())[0]
        self.assertEqual(f._fields, ("level", "line", "msg"))


class Iteration1(Base):
    """Eval iteration 1 fixes: quotes-only mode, prose runs already quoted, multi-passage frontmatter."""

    def qo(self, text, lang="en"):
        p = Path(self.tmp) / "chat.md"
        p.write_text(text, encoding="utf-8")
        return check(p, self.conn, quotes_only=True, lang=lang)

    def test_quotes_only_skips_sermon_checks(self):
        fs = self.qo("Chat answer about λόγος.\n\n" + J11)
        self.assertEqual(fs, [])

    def test_quotes_only_still_checks_quotes_tags_tradition(self):
        bad = self.qo("> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγοςς\n> Literal: a\n> Natural: b\n")
        self.assertTrue(any("not found" in f.msg for f in bad if f.level == "ERROR"))
        tag = self.qo("> [GRC: John.1.1] καὶ θεὸς\n> Literal: a\n> Natural: b\n")
        self.assertTrue(any("unparseable" in f.msg for f in tag if f.level == "ERROR"))
        trad = self.qo(J11.replace("the word was God", "the church"))
        self.assertTrue(any("tradition term" in f.msg for f in trad if f.level == "ERROR"))
        es = self.qo(J11.replace("the word was God", "la iglesia"), lang="es")
        self.assertTrue(any("tradition term" in f.msg for f in es if f.level == "ERROR"))
        self.assertFalse(any("tradition term" in f.msg for f in self.qo(J11.replace("the word was God", "la iglesia"))))

    def test_quotes_only_without_lang_scans_es_and_en(self):
        for nat in ("la iglesia", "the church"):
            fs = self.qo(J11.replace("the word was God", nat), lang=None)
            self.assertTrue(any("tradition term" in f.msg for f in fs if f.level == "ERROR"), nat)
            self.assertFalse([f for f in fs if f.level == "WARN"], fs)

    def test_cross_chapter_quote_says_split(self):
        q = "> [GRC John.7.53-8.11] καὶ\n> Literal: a\n> Natural: b\n"
        fs = self.qo(q)
        self.assertTrue(any("crosses a chapter; split it" in f.msg for f in fs if f.level == "ERROR"), fs)

    def test_quotes_only_cli(self):
        p = Path(self.tmp) / "chat2.md"
        p.write_text(J11, encoding="utf-8")
        env = {**os.environ, "OTS_DB": self.dbfile}
        r = subprocess.run([sys.executable, str(CHECK), "--quotes-only", "--lang", "es", str(p)],
                           capture_output=True, text=True, env=env)
        self.assertEqual((r.returncode, r.stdout), (0, f"OK {p}\n"))

    def test_prose_run_already_quoted_is_exempt(self):
        t = fm(template="custom", sections="Text, Notes") + "## Text\n\n" + J11 + "\nSo καὶ θεὸς ἦν, says John.\n\n## Notes\n\nx\n"
        self.assertFalse(any("untagged original-language" in f.msg for f in self.run_text(t)))
        before = fm(template="custom", sections="Text, Notes") + "## Text\n\nSo καὶ θεὸς ἦν, says John.\n\n" + J11 + "\n## Notes\n\nx\n"
        self.assertTrue(any("untagged original-language" in f.msg for f in self.run_text(before)))
        other = fm(template="custom", sections="Text, Notes") + "## Text\n\n" + J11 + "\nSo ὁ λόγος σὰρξ ἐγένετο.\n\n## Notes\n\nx\n"
        self.assertTrue(any("untagged original-language" in f.msg for f in self.run_text(other)))

    def test_multi_passage_frontmatter(self):
        fs = self.run_text(fm(passage="John.7.53; John.8.1-11; Mark.16.9-20") + body())
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)


PROBES = dict(
    notes_untagged="- John.1.1 contested. TR adds: ἐν τῷ οὐρανῷ ὁ πατὴρ ὁ λόγος",
)


class FinalReview(Base):
    """Whole-branch review: untagged text anywhere in the body, inline tags, fail-closed modes, EXT brackets."""

    def doc(self, notes="- John.1.1 options.", prose="prose", quote=J11):
        return fm() + body(notes=notes, prose=prose, quote=quote)

    def errs(self, text, quotes_only=False):
        p = Path(self.tmp) / "fr.md"
        p.write_text(text, encoding="utf-8")
        return [f.msg for f in check(p, self.conn, quotes_only=quotes_only) if f.level == "ERROR"]

    def test_untagged_run_in_notes_errors(self):
        e = self.errs(self.doc(notes=PROBES["notes_untagged"]))
        self.assertTrue(any("untagged original-language text" in m for m in e), e)

    def test_two_word_run_in_prose_errors(self):
        e = self.errs(self.doc(prose="The text says θεὸς ἀγαθός here."))
        self.assertTrue(any("untagged original-language text" in m for m in e), e)

    def test_single_words_allowed(self):
        self.assertEqual(self.errs(self.doc(prose="The lemma λόγος, then θεός.", notes="- John.1.1: λόγος / θεός")), [])

    def test_inline_tag_verified(self):
        ok = self.doc(notes="- John.1.1 options; [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος is the clause.")
        self.assertEqual(self.errs(ok), [])
        bad = self.doc(notes="- John.1.1 options; [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος ἀγαθός here.")
        self.assertTrue(any("not found" in m for m in self.errs(bad)))
        self.assertTrue(any("not found" in m for m in self.errs(self.doc(prose="- [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος ἀγαθός ἐστιν"))))
        unknown = self.doc(notes="- John.1.1 [FOO John.1.1] σὰρξ ἐγένετο here")
        self.assertTrue(any("untagged original-language text" in m for m in self.errs(unknown)))

    def test_inline_tag_ellipsis(self):
        ok = self.doc(notes="- John.1.1: [GRC John.1.1] ἐν ἀρχῇ … καὶ θεὸς ἦν ὁ λόγος")
        self.assertEqual(self.errs(ok), [])

    def test_quotes_only_ignores_frontmatter_lookalike(self):
        e = self.errs("---\nnote: x\n\n> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος ἀγαθός\n> Literal: a\n> Natural: b\n",
                      quotes_only=True)
        self.assertTrue(any("not found" in m for m in e), e)

    def test_quotes_only_without_quotes_errors(self):
        self.assertTrue(any("no tagged quotes" in m for m in self.errs("", quotes_only=True)))
        self.assertTrue(any("no tagged quotes" in m for m in self.errs("just prose", quotes_only=True)))
        self.assertEqual(self.errs("prose [GRC John.1.1] καὶ θεὸς ἦν", quotes_only=True), [])

    def test_unterminated_frontmatter_errors(self):
        t = "---\npassage: John.1.1\nlanguage: en\ntemplate: custom\nsections: Text, Notes\n\n## Text\n" + J11 + "## Notes\n"
        self.assertTrue(any("unterminated frontmatter" in m for m in self.errs(t)))

    def ext_quote(self):
        t = self.conn.execute("select text from verses where corpus='ext' and witness='Josephus' and ref='Ant.18.63'").fetchone()[0]
        return "> [EXT:Josephus Ant.18.63] " + " ".join(t.split()[:4]) + "\n> Literal: a\n> Natural: b\n"

    def test_ext_bracketed_quote_needs_note(self):
        e = self.errs(self.doc(quote=self.ext_quote()))
        self.assertTrue(any("editor-bracketed" in m for m in e), e)
        p = Path(self.tmp) / "fr2.md"
        p.write_text(self.doc(quote=self.ext_quote(), notes="- Ant.18.63: the editor brackets this passage."), encoding="utf-8")
        fs = check(p, self.conn)
        self.assertFalse([f for f in fs if "editor-bracketed" in f.msg and f.level == "ERROR"], fs)
        self.assertTrue([f for f in fs if "editor-bracketed" in f.msg and f.level == "WARN"], fs)

    def ext_errs(self, notes, quote=None):
        return [f for f in check(self._qo_doc(self.doc(quote=quote or self.ext_quote(), notes=notes)), self.conn)
                if f.level == "ERROR" and "editor-bracketed" in f.msg]

    def _qo_doc(self, text):
        p = Path(self.tmp) / "fr3.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_ext_bracket_note_must_name_ref(self):
        notes = "- John.1.1 options.\n- Mark.16.9: editors enclose [[ ]] the long ending."
        self.assertTrue(self.ext_errs(notes))
        self.assertTrue(self.ext_errs("- Ant.18.63 is a testimonium.\n- elsewhere the editor brackets things."))

    def test_ext_bracket_note_same_line_ok(self):
        self.assertFalse(self.ext_errs("- Ant.18.63 \u2014 editor-bracketed in Niese"))
        self.assertFalse(self.ext_errs("- Ant.18.63\n  editor-bracketed in Niese"))
        self.assertFalse(self.ext_errs("- Ant.18.63-64: corchetes del editor"))

    def test_ext_bracket_inline_same_line_ok(self):
        t = self.conn.execute("select text from verses where corpus='ext' and witness='Josephus' and ref='Ant.18.63'").fetchone()[0]
        q = " ".join(t.split()[:4])
        e = self.errs(self.doc(prose=f"The editor brackets [EXT:Josephus Ant.18.63] {q} here."))
        self.assertFalse([m for m in e if "editor-bracketed" in m], e)

    def test_bom_before_frontmatter(self):
        p = Path(self.tmp) / "bom.md"
        p.write_text("\ufeff" + self.doc(), encoding="utf-8")
        self.assertFalse([f for f in check(p, self.conn) if "frontmatter" in f.msg], [f.msg for f in check(p, self.conn)])

    def test_lemma_list_allowed(self):
        for prose in ("Related lemmas: \u03b2\u03ac\u03c0\u03c4\u03b9\u03c3\u03bc\u03b1, \u03b2\u03b1\u03c0\u03c4\u03b9\u03c3\u03bc\u03cc\u03c2 / \u03b2\u03b1\u03c0\u03c4\u03b9\u03c3\u03bc\u03bf\u1fe6",
                      "lemmas \u03ba\u03b1\u03af, \u03b8\u03b5\u03cc\u03c2; \u03bb\u03cc\u03b3\u03bf\u03c2 \u00b7 \u1f26\u03bd",
                      "lemmas \u03ba\u03b1\u03af\u037e \u03b8\u03b5\u03cc\u03c2\u0387 \u03bb\u03cc\u03b3\u03bf\u03c2"):
            self.assertEqual(self.errs(self.doc(prose=prose)), [], prose)

    def test_long_separated_list_warns(self):
        def w(prose):
            p = self._qo_doc(self.doc(prose=prose))
            return [f for f in check(p, self.conn) if "separated original-language" in f.msg]
        self.assertTrue(w("The words \u03ba\u03b1\u03af, \u1f10\u03b3\u03ad\u03bd\u03b5\u03c4\u03bf, \u03c6\u1ff6\u03c2, \u03bc\u03ad\u03b3\u03b1, \u03b8\u03b5\u03cc\u03c2 here."))
        self.assertFalse(w("The words \u03ba\u03b1\u03af, \u1f10\u03b3\u03ad\u03bd\u03b5\u03c4\u03bf, \u03c6\u1ff6\u03c2, \u03bc\u03ad\u03b3\u03b1 here."))

    def test_list_cap_any_separator(self):
        def w(prose):
            p = self._qo_doc(self.doc(prose=prose))
            return [f for f in check(p, self.conn) if "separated original-language" in f.msg]
        five = ["\u03ba\u03b1\u03af", "\u1f10\u03b3\u03ad\u03bd\u03b5\u03c4\u03bf", "\u03c6\u1ff6\u03c2", "\u03bc\u03ad\u03b3\u03b1", "\u03b8\u03b5\u03cc\u03c2"]
        for sep in (" \u2014 ", " - ", " \u2013 "):
            self.assertTrue(w("Words " + sep.join(five) + " here."), repr(sep))
            self.assertFalse(w("Words " + sep.join(five[:4]) + " here."), repr(sep))
        self.assertTrue(w("Words (" + ") (".join(five) + ") here."))
        self.assertTrue(w("Words " + "\n".join(five) + "\nhere."))
        self.assertTrue(w("Words " + five[0] + " (" + five[1] + ") \u2014 " + ", ".join(five[2:]) + "."))
        self.assertFalse(w("Run `word " + "`, `word ".join(five) + "` here."))  # command snippets do not count
        # wrapped bullet lines count together; a new bullet starts a fresh count
        self.assertTrue(w("- " + " \u2014 ".join(five[:3]) + "\n  " + " \u2014 ".join(five[3:])))
        self.assertFalse(w("- " + " \u2014 ".join(five[:3]) + "\n- " + " \u2014 ".join(five[3:])))

    def test_slash_separated_lists(self):
        def w(prose):
            p = self._qo_doc(self.doc(prose=prose))
            return [f for f in check(p, self.conn) if "separated original-language" in f.msg]
        five = ["\u03ba\u03b1\u03af", "\u1f10\u03b3\u03ad\u03bd\u03b5\u03c4\u03bf", "\u03c6\u1ff6\u03c2", "\u03bc\u03ad\u03b3\u03b1", "\u03b8\u03b5\u03cc\u03c2"]
        self.assertTrue(w("Words " + " / ".join(five) + " here."))
        self.assertFalse(w("Words " + " / ".join(five[:4]) + " here."))
        self.assertTrue(w("Words " + ", ".join(five[:2]) + " / " + ", ".join(five[2:]) + " here."))
        self.assertTrue(w("Words " + " / ".join(five[:2]) + ", " + ", ".join(five[2:]) + " here."))

    def test_inline_tag_does_not_absorb_slash_word(self):
        e = self.errs(self.doc(notes="- John.1.1 options; [GRC John.1.1] \u03ba\u03b1\u1f76 \u03b8\u03b5\u1f78\u03c2 \u1f26\u03bd \u1f41 \u03bb\u03cc\u03b3\u03bf\u03c2 / \u03c6\u1ff6\u03c2 here."))
        self.assertEqual(e, [])

    def test_two_adjacent_words_still_error(self):
        for prose in ("\u03ba\u03b1\u1f76 \u03b8\u03b5\u1f78\u03c2 here", "\u03ba\u03b1\u1f76 \u03b8\u03b5\u1f78\u03c2 \u1f26\u03bd \u1f41 \u03bb\u03cc\u03b3\u03bf\u03c2",
                      "\u03ba\u03b1\u1f76, \u03b8\u03b5\u1f78\u03c2 \u1f26\u03bd \u1f41 \u03bb\u03cc\u03b3\u03bf\u03c2"):
            self.assertTrue(any("untagged" in m for m in self.errs(self.doc(prose=prose))), prose)

    def test_baptiz_stems(self):
        q = "> [GRC John.1.1] καὶ θεὸς\n> Literal: a\n> Natural: {}\n"
        cases = [("es", "id y bautizad"), ("es", "bautizarlos"), ("es", "yo bautizo"), ("es", "que se bautícen"),
                 ("en", "they were baptizing them"), ("en", "a baptismal pool"), ("es", "evangelizar")]
        for lang, nat in cases:
            e = [f.msg for f in check(self._qo(q.format(nat)), self.conn, quotes_only=True, lang=lang) if f.level == "ERROR"]
            self.assertTrue(any("tradition term" in m for m in e), (nat, e))
        clean = [f for f in check(self._qo(q.format("sumergir, lavar; the bath")), self.conn, quotes_only=True, lang="es")
                 if f.level == "ERROR"]
        self.assertEqual(clean, [])

    def _qo(self, text):
        p = Path(self.tmp) / "qo.md"
        p.write_text(text, encoding="utf-8")
        return p


if __name__ == "__main__":
    unittest.main()
