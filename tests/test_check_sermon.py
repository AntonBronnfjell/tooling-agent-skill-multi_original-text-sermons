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
    "language-unsupported": "language",
    "range-nonexistent": "not found",
    "range-giant": "range",
    "chapter-only": "chapter",
}


class Hardening(Base):
    def test_negative_fixtures_error_with_message(self):
        for name, frag in NEG_ERR.items():
            errs = [f.msg for f in check(FX / "negative" / f"{name}.md", self.conn) if f.level == "ERROR"]
            self.assertTrue(any(frag in m for m in errs), (name, errs))

    def test_stitched_single_words_warns(self):
        fs = check(FX / "negative" / "stitched-single-words.md", self.conn)
        self.assertFalse([f for f in fs if f.level == "ERROR"], fs)
        self.assertTrue(any("one-word" in f.msg for f in fs if f.level == "WARN"))
        self.assertTrue(any("segments" in f.msg for f in fs if f.level == "WARN"))

    def test_prose_greek_run_warns(self):
        t = fm(template="custom", sections="Text, Notes") + "## Text\n\nκαὶ θεὸς ἦν ὁ λόγος here\n\n## Notes\n\nx\n"
        self.assertTrue(any("original-language words in prose" in f.msg for f in self.run_text(t) if f.level == "WARN"))
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
        self.assertFalse(any("tradition term" in m for m in self.errs(mk("bautizándolosmente"))))
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


if __name__ == "__main__":
    unittest.main()
