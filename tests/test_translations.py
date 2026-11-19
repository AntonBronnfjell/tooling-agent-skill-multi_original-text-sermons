import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import build_db  # noqa: E402
from test_build_stepbible import FIXTURES, build  # noqa: E402


class Translations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"), only=("translations",))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def test_kjv(self):
        self.assertIn("Word was God", self.q("select text from translations where version='KJV' and ref='John.1.1'")["text"])

    def test_rv1909(self):
        r = self.q("select lang from translations where version='RV1909' and ref='John.1.1'")
        self.assertEqual(r["lang"], "es")

    def test_lang_en_and_omitted_skipped(self):
        self.assertEqual(self.q("select lang from translations where version='KJV' limit 1")["lang"], "en")
        self.assertIsNone(self.q("select 1 from translations where version='Reina1569'"))

    def test_osis_refs_and_brackets_kept(self):
        self.assertIsNotNone(self.q("select 1 from translations where version='KJV' and ref='1John.5.7'"))
        self.assertIsNotNone(self.q("select 1 from translations where version='KJV' and ref='Ps.51.1'"))
        self.assertIsNotNone(self.q("select 1 from translations where version='KJV' and ref='Mal.4.1'"))
        self.assertIsNotNone(self.q("select 1 from translations where version='KJV' and text like '%[%]%'"))

    def test_all_refs_canonical(self):
        for r in self.conn.execute("select distinct ref from translations"):
            self.assertRegex(r["ref"], r"^[0-9A-Za-z]+\.\d+\.\d+$")

    def test_no_empty_text(self):
        self.assertIsNone(self.q("select 1 from translations where trim(text)=''"))

    def test_user_csv(self):
        self.assertIsNotNone(self.q("select 1 from translations where version='TEST' and ref='John.1.1'"))
        self.assertEqual(self.q("select lang from translations where version='TEST' limit 1")["lang"], "es")

    def test_user_csv_quoting(self):
        t = self.q("select text from translations where version='TEST' and ref='John.3.16'")["text"]
        self.assertIn('"amó"', t)
        t = self.q("select text from translations where version='TEST' and ref='John.1.1'")["text"]
        self.assertIn("Verbo, y el Verbo", t)

    def test_user_csv_bad_ref_skipped_and_reported(self):
        self.assertEqual(self.q("select count(*) c from translations where version='TEST'")["c"], 2)
        out = io.StringIO()
        from loaders import translations
        c = _mem()
        self.addCleanup(c.close)
        translations.load(c, FIXTURES, out=out)
        self.assertIn("NoSuchBook", out.getvalue())
        self.assertIn("1 unparseable", out.getvalue())


def _mem():
    import sqlite3
    from otslib import db
    c = sqlite3.connect(":memory:")
    c.executescript(db.SCHEMA)
    return c


class BuildHardError(unittest.TestCase):
    def test_missing_loader_module_is_hard_error(self):
        import importlib
        orig = importlib.import_module

        def fake(name, *a, **k):
            if name == "loaders.ext":
                raise ModuleNotFoundError("nope", name="loaders.ext")
            return orig(name, *a, **k)
        importlib.import_module = fake
        try:
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ModuleNotFoundError):
                    build_db.build(FIXTURES, Path(d) / "x.db", only=["ext"], out=io.StringIO())
        finally:
            importlib.import_module = orig


if __name__ == "__main__":
    unittest.main()
