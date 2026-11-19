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

from loaders import macula  # noqa: E402
from otslib import norm  # noqa: E402
from test_build_stepbible import FIXTURES, build  # noqa: E402


class MaculaEnrich(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"),
                         only=("stepbible", "versification", "macula"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def test_logos_domain(self):
        r = self.q("select domain from words where corpus='grnt' and witness='TAGNT' and ref='John.1.1' "
                   "and lemma='λόγος' limit 1")
        self.assertTrue(r["domain"])
        self.assertRegex(r["domain"], r"^\d+\.\d+")  # Louw-Nida

    def test_greek_role(self):
        r = self.q("select syntax_role from words where corpus='grnt' and witness='TAGNT' and ref='John.1.1' "
                   "and syntax_role is not null and syntax_role<>'' limit 1")
        self.assertTrue(r["syntax_role"])

    def test_other_witness_words_untouched(self):
        r = self.q("select count(*) n from words where corpus='grnt' and editions not like '%SBL%' and domain<>''")
        self.assertEqual(r["n"], 0)

    def test_hebrew_role(self):
        self.assertTrue(self.q("select syntax_role from words where corpus='hebot' and ref='Gen.1.1' "
                               "and syntax_role is not null and syntax_role<>'' limit 1"))

    def test_hebrew_domain(self):
        self.assertTrue(self.q("select domain from words where corpus='hebot' and ref='Gen.1.1' "
                               "and domain<>'' limit 1"))

    def test_sbl_mark_16_added(self):
        r = self.q("select text, match_key from verses where corpus='grnt' and witness='SBL' and ref='Mark.16.9'")
        self.assertIsNotNone(r)
        self.assertTrue(r["text"].startswith("Ἀναστὰς δὲ"))

    def test_sbl_mark_16_17_full_verse(self):
        r = self.q("select text from verses where corpus='grnt' and witness='SBL' and ref='Mark.16.17'")
        self.assertGreaterEqual(len(r["text"].split()), 15)
        self.assertTrue(r["text"].startswith("σημεῖα δὲ"))

    def sbl(self, ref):
        return self.q("select text from verses where corpus='grnt' and witness='SBL' and ref=?", ref)["text"]

    def test_verse_boundaries_follow_kjv_refs_gal_2_19_20(self):
        self.assertTrue(self.sbl("Gal.2.19").endswith("ζήσω·"))
        self.assertTrue(self.sbl("Gal.2.20").startswith("Χριστῷ συνεσταύρωμαι"))

    def test_verse_boundaries_rom_9_11_12(self):
        self.assertTrue(self.sbl("Rom.9.11").endswith("ἐκ τοῦ καλοῦντος,"))
        self.assertTrue(self.sbl("Rom.9.12").startswith("ἐρρέθη αὐτῇ"))

    def test_swapped_verses_phil_1_16_17_follow_kjv_order(self):
        self.assertTrue(self.sbl("Phil.1.16").startswith("οἱ δὲ ἐξ ἐριθείας"))
        self.assertTrue(self.sbl("Phil.1.17").startswith("οἱ μὲν ἐξ ἀγάπης"))

    def test_sbl_verses_line_up_with_tagnt_sbl_words(self):
        """every verse that has TAGNT SBL words starts with the same word as its first TAGNT SBL word"""
        rows = self.conn.execute(
            "SELECT ref, MIN(pos) p FROM words WHERE corpus='grnt' AND witness='TAGNT' "
            "AND ref IN ('Gal.2.19','Gal.2.20','Rom.9.11','Rom.9.12','Phil.1.16','Phil.1.17') "
            "AND editions LIKE '%SBL%' GROUP BY ref").fetchall()
        self.assertEqual(len(rows), 6)
        for r in rows:
            first = self.q("SELECT surface FROM words WHERE corpus='grnt' AND witness='TAGNT' AND ref=? AND pos=?",
                           r["ref"], r["p"])["surface"]
            self.assertEqual(macula._wkey(first), macula._wkey(self.sbl(r["ref"]).split()[0]), r["ref"])

    def test_no_editorial_brackets(self):
        n = self.q("select count(*) n from verses where corpus='grnt' and witness='SBL' "
                   "and (text like '%[%' or text like '%]%' or text like '%⟦%')")["n"]
        self.assertEqual(n, 0)

    def test_sbl_verse_text_exact(self):
        r = self.q("select text from verses where corpus='grnt' and witness='SBL' and ref='John.1.1'")
        self.assertEqual(r["text"], "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος.")


class MaculaReplace(unittest.TestCase):
    def test_fragment_is_replaced(self):
        tmp = tempfile.mkdtemp()
        try:
            conn = build(FIXTURES, os.path.join(tmp, "t.db"), only=("versification",))
            conn.execute("insert into verses values ('grnt','SBL','Mark.16.17','ταῦτα παρακολουθήσει·','x')")
            conn.execute("insert into verses values ('grnt','TR','Mark.16.17','keep me','x')")
            stats = macula.load_greek(conn, FIXTURES / "macula")
            self.assertEqual(stats["replaced_different"], 1)
            self.assertGreater(stats["added"], 0)
            n = conn.execute("select count(*) from verses where witness='SBL' and ref='Mark.16.17'").fetchone()[0]
            self.assertEqual(n, 1)
            tr = conn.execute("select text from verses where witness='TR' and ref='Mark.16.17'").fetchone()[0]
            self.assertEqual(tr, "keep me")
            full = conn.execute("select text from verses where witness='SBL' and ref='Mark.16.17'").fetchone()[0]
            self.assertGreaterEqual(len(full.split()), 15)
            conn.close()
        finally:
            shutil.rmtree(tmp)

    def test_token_spacing(self):
        self.assertEqual(macula._token("δι", "’") + macula._token("οὗ", " "), "δι’ οὗ ")
        self.assertEqual(macula._token("Χριστός", ";"), "Χριστός; ")

    def test_faithlife_word_fixes(self):
        # the published SBLGNT (Faithlife) wins where MACULA's surface form differs
        self.assertEqual(macula.faithlife_fix("John.7.34", "εὑρήσετέ"), "εὑρήσετε")
        self.assertEqual(macula.faithlife_fix("John.8.5", "Μωϋσῆς"), "Μωσῆς")
        self.assertEqual(macula.faithlife_fix("John.10.29", "ἐστιν"), "ἐστίν")
        self.assertEqual(macula.faithlife_fix("Luke.8.20", "θέλοντές"), "θέλοντες")
        # same word elsewhere is left alone
        self.assertEqual(macula.faithlife_fix("John.7.36", "ἐστιν"), "ἐστιν")

    def test_brackets_dropped(self):
        self.assertEqual(macula.clean("[[καὶ]]"), "καὶ")
        self.assertEqual(macula.clean("[τοῦ]"), "τοῦ")


if __name__ == "__main__":
    unittest.main()
