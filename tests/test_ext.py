import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_build_stepbible import FIXTURES, build  # noqa: E402


class Ext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"), only=("ext",))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def test_josephus_section_has_ekklesia(self):
        self.assertIsNotNone(self.q("select 1 from words where corpus='ext' and witness='Josephus' and surface like 'ἐκκλησ%'"))

    def test_ext_ref_format(self):
        r = self.q("select ref from verses where corpus='ext' and witness='Josephus' limit 1")["ref"]
        self.assertRegex(r, r"^[A-Za-z]+\.\d+\.\d+$")

    def test_all_refs_three_parts(self):
        for r in self.conn.execute("select ref from verses where corpus='ext'"):
            self.assertRegex(r["ref"], r"^[A-Za-z]+\.\d+\.\d+$")

    def test_ant_3_84(self):
        t = self.q("select text, match_key from verses where corpus='ext' and witness='Josephus' and ref='Ant.3.84'")
        self.assertIn("ἐκκλησίαν", t["text"])
        self.assertIn("ἐκκλησίαν", t["match_key"])

    def test_non_numeric_section_skipped(self):
        self.assertIsNone(self.q("select 1 from verses where ref like '%arg%'"))

    def test_apparatus_excluded(self):
        # headings/labels are not part of section text
        self.assertIsNone(self.q("select 1 from verses where corpus='ext' and text like '%ΦΙΛΩΝ%'"))

    def test_ant_18_63_testimonium_kept_and_bracketed(self):
        t = self.q("select text from verses where corpus='ext' and witness='Josephus' and ref='Ant.18.63'")
        self.assertIsNotNone(t)
        self.assertIn("Ἰησοῦς", t["text"])
        r = self.q("select count(*) n from words where corpus='ext' and ref='Ant.18.63' and editions='bracketed'")
        self.assertGreater(r["n"], 0)
        # ordinary sections carry no flag
        self.assertIsNone(self.q("select 1 from words where corpus='ext' and ref='Ant.3.84' and editions!=''"))

    def test_ant_18_64_present(self):
        self.assertIsNotNone(self.q("select 1 from verses where corpus='ext' and ref='Ant.18.64'"))

    def test_pb_tail_preserved(self):
        t = self.q("select text from verses where corpus='ext' and ref='Ant.3.84'")["text"]
        self.assertIn("ἀκούσεσθαι, ὁ μὲν θεός", t)  # text after <pb/> and <q> kept

    def test_skipped_count_excludes_18_63(self):
        import io
        from loaders import ext
        out = io.StringIO()
        import sqlite3
        from otslib import db
        c = sqlite3.connect(":memory:")
        self.addCleanup(c.close)
        c.executescript(db.SCHEMA)
        ext.load(c, FIXTURES, out)
        self.assertIn("0 sections skipped", out.getvalue())

    def test_philo_decal(self):
        t = self.q("select text from verses where corpus='ext' and witness='Philo' and ref='Decal.1.32'")
        self.assertIsNotNone(t)
        self.assertIn("ἐκκλησ", t["text"])

    def test_word_rows(self):
        r = self.q("select min(pos) a, count(*) n, sum(lemma!='') l from words where corpus='ext' and ref='Ant.3.84'")
        self.assertEqual((r["a"], r["l"]), (1, 0))
        self.assertGreater(r["n"], 5)
        self.assertIsNone(self.q("select 1 from words where corpus='ext' and (surface='' or surface glob '*[.,;·]*')"))

    def test_papyri_vocab(self):
        self.assertIsNotNone(self.q("select 1 from papyri_vocab where lemma='ἐκκλησία'"))
        e = self.q("select entry from papyri_vocab where lemma='ἐκκλησία'")["entry"]
        self.assertIn("Biblical history", e)
        self.assertIsNone(self.q("select 1 from papyri_vocab where lemma like '%.' or lemma like '%,'"))

    def test_papyri_quality_meta(self):
        self.assertEqual(self.q("select value from meta where key='papyri_quality'")["value"], "noisy-ocr")


if __name__ == "__main__":
    unittest.main()
