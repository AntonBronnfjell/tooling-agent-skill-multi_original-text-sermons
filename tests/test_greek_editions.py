"""TR and Byz verse text from the vendored printed editions (loaders/greek_editions.py)."""
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


class GroundTruthEditions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"),
                         only=("stepbible", "versification", "macula", "greek_editions"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def text_or_none(self, wit, ref):
        r = self.conn.execute("SELECT text FROM verses WHERE corpus='grnt' AND witness=? AND ref=?",
                              (wit, ref)).fetchall()
        self.assertLessEqual(len(r), 1, (wit, ref))
        return r[0]["text"] if r else None

    def text(self, wit, ref):
        t = self.text_or_none(wit, ref)
        self.assertIsNotNone(t, (wit, ref))
        return t

    def flags(self, wit):
        return {r["ref"]: r["reason"] for r in self.conn.execute(
            "SELECT ref, reason FROM order_flags WHERE corpus='grnt' AND witness=?", (wit,))}

    # -- brief

    def test_tr_1tim_1_1(self):
        self.assertIn("Ἰησοῦ Χριστοῦ", self.text("TR", "1Tim.1.1"))

    def test_tr_byz_acts_20_28(self):
        for w in ("TR", "Byz"):
            self.assertIn("τοῦ ἰδίου αἵματος", self.text(w, "Acts.20.28"))

    def test_mark_7_30_not_scrambled(self):
        self.assertNotIn("τὴν τὸ", self.text("TR", "Mark.7.30"))

    def test_kjv_refs(self):  # source numbering mapped to KJV refs
        self.assertTrue(self.text("Byz", "3John.1.14"))
        self.assertIsNone(self.text_or_none("Byz", "3John.1.15"))

    # -- exact ground-truth text (TAGNT order marks scramble these)

    def test_exact_text(self):
        self.assertEqual(self.text("TR", "Mark.7.30"), "Καὶ ἀπελθοῦσα εἰς τὸν οἶκον αὐτῆς, εὗρε τὸ δαιμόνιον "
                         "ἐξεληλυθός, καὶ τὴν θυγατέρα βεβλημένην ἐπὶ τῆς κλίνης.")
        self.assertEqual(self.text("Byz", "2Pet.1.18"), "καὶ ταύτην τὴν φωνὴν ἡμεῖς ἠκούσαμεν ἐξ οὐρανοῦ "
                         "ἐνεχθεῖσαν, σὺν αὐτῷ ὄντες ἐν τῷ ὄρει τῷ ἁγίῳ.")
        for w in ("TR", "Byz"):
            self.assertTrue(self.text(w, "Luke.15.30").endswith("τὸν μόσχον τὸν σιτευτόν."), w)
        self.assertIn("ἀπόστολος Ἰησοῦ χριστοῦ κατ’", self.text("Byz", "1Tim.1.1"))

    def test_tr_1john_5_7_printed_text(self):  # TAGNT word rows carry the erratum ἕν τῷ οὐρανῷ
        self.assertIn("οἱ μαρτυροῦντες ἐν τῷ οὐρανῷ, ὁ πατήρ, ὁ λόγος,", self.text("TR", "1John.5.7"))
        self.assertEqual(self.text("Byz", "1John.5.7"), "Ὅτι τρεῖς εἰσὶν οἱ μαρτυροῦντες,")

    def test_paragraph_marks_stripped(self):
        self.assertTrue(self.text("Byz", "Matt.23.14").startswith("Οὐαὶ δὲ ὑμῖν"))
        n = self.conn.execute("SELECT count(*) FROM verses WHERE text LIKE '%¶%'").fetchone()[0]
        self.assertEqual(n, 0)

    def test_3john_1_14_whole_verse_both_witnesses(self):
        for w in ("TR", "Byz"):
            t = self.text(w, "3John.1.14")
            self.assertTrue(t.startswith("ἐλπίζω δὲ εὐθέως ἰδεῖν σε"), w)
            self.assertIn("Εἰρήνη σοι.", t)
            self.assertTrue(t.endswith("κατ’ ὄνομα.") or t.endswith("κατ᾿ ὄνομα."), w)
            self.assertIsNone(self.text_or_none(w, "3John.1.15"))

    def test_byz_rom_16_25_27_printed_after_14_23_lands_on_kjv_refs(self):
        self.assertTrue(self.text("Byz", "Rom.16.25").startswith("Τῷ δὲ δυναμένῳ"))
        self.assertTrue(self.text("Byz", "Rom.16.26").startswith("φανερωθέντος δὲ νῦν"))
        self.assertEqual(self.text("Byz", "Rom.16.27"), "μόνῳ σοφῷ θεῷ, διὰ Ἰησοῦ χριστοῦ, ᾧ ἡ δόξα εἰς τοὺς αἰῶνας. Ἀμήν.")
        self.assertTrue(self.text("Byz", "Rom.14.23").endswith("ἁμαρτία ἐστίν."))
        self.assertTrue(self.text("Byz", "Rom.16.24").startswith("Ἡ χάρις"))
        for ref in ("Rom.14.24", "Rom.14.25", "Rom.14.26"):
            self.assertIsNone(self.text_or_none("Byz", ref))

    def test_byz_matt_23_13_14_swapped_verses_follow_kjv(self):
        self.assertIn("κλείετε", self.text("Byz", "Matt.23.13"))
        self.assertNotIn("κατεσθίετε", self.text("Byz", "Matt.23.13"))
        self.assertIn("κατεσθίετε", self.text("Byz", "Matt.23.14"))
        self.assertTrue(self.text("Byz", "Matt.23.13").startswith("Οὐαὶ ὑμῖν"))
        self.assertIn("κλείετε", self.text("TR", "Matt.23.13"))  # TR prints them in KJV order

    def test_single_reordered_word_stays_in_its_printed_verse(self):
        """TAGNT keeps κλοπαί in Mark 7:21 (NA order); TR/Byz (and the KJV) begin 7:22 with it."""
        for w in ("TR", "Byz"):
            self.assertTrue(self.text(w, "Mark.7.21").endswith("μοιχεῖαι, πορνεῖαι, φόνοι,"), w)
            self.assertTrue(self.text(w, "Mark.7.22").startswith("κλοπαί, πλεονεξίαι"), w)

    def test_match_key_matches_text(self):
        from otslib import norm
        for r in self.conn.execute("SELECT text, match_key FROM verses WHERE witness IN ('TR','Byz')"):
            self.assertEqual(r["match_key"], norm.match_key(r["text"], "grc"))

    # -- flags and provenance

    def test_tr_verse_differing_from_scrivener_keeps_tagnt_text_and_is_flagged(self):
        # eBible grctr Rom 16:27 has ᾧ, Robinson's Scrivener 1894 does not: not ground truth
        self.assertEqual(self.flags("TR").get("Rom.16.27"), "no ground truth")
        self.assertNotIn("Rom.16.25", self.flags("TR"))

    def test_verse_without_ground_truth_keeps_tagnt_text_and_is_flagged(self):
        self.assertEqual(self.flags("TR").get("John.1.1"), "no ground truth")
        self.assertEqual(self.flags("Byz").get("John.1.1"), "no ground truth")
        self.assertTrue(self.text("TR", "John.1.1").startswith("Ἐν ἀρχῇ"))

    def test_ground_truth_verses_not_flagged(self):
        for w in ("TR", "Byz"):
            for ref in ("1Tim.1.1", "Acts.20.28", "Mark.7.30", "2Pet.1.18", "Luke.15.30", "3John.1.14", "Rom.16.24"):
                self.assertNotIn(ref, self.flags(w), (w, ref))

    def test_other_witnesses_and_words_untouched(self):
        self.assertEqual(self.text("SBL", "John.1.1"),
                         "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος.")
        self.assertTrue(self.text("NA", "Acts.20.28").endswith("διὰ τοῦ αἵματος τοῦ ἰδίου."))
        n = self.conn.execute("SELECT count(*) FROM words WHERE corpus='grnt' AND ref='Mark.7.30'").fetchone()[0]
        self.assertGreater(n, 10)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM order_flags WHERE witness NOT IN ('TR','Byz')")
                         .fetchone()[0], 0)

    def test_meta_sources(self):
        meta = dict(self.conn.execute("SELECT key, value FROM meta").fetchall())
        self.assertIn("Scrivener 1894", meta["tr_source"])
        self.assertIn("Robinson-Pierpont", meta["byz_source"])


class VerifyAgainstScrivener(unittest.TestCase):
    def setUp(self):
        from loaders import greek_editions
        self.v = greek_editions.verify

    def test_movable_nu_case_accents_ignored(self):
        self.assertEqual(self.v("Ἡ χάρις ἐστί, πᾶσι.".split(), "h cariv estin pasin".replace("v", "s").split()), 4)

    def test_word_division_ignored(self):
        self.assertEqual(self.v("εἴκοσι τρεῖς".split(), ["eikositreis"]), 2)

    def test_trailing_subscription_cut(self):
        words = "ὑμῶν. Ἀμήν. Πρὸς Ῥωμαίους ἐγράφη".split()
        self.assertEqual(self.v(words, ["umwn", "amhn"]), 2)

    def test_real_difference_rejected(self):
        self.assertIsNone(self.v("εὗρον τὸ παιδίον".split(), ["eidon", "to", "paidion"]))
        self.assertIsNone(self.v("ἔχει".split(), ["ecein"]))  # infinitive vs 3sg is not movable nu
        self.assertIsNone(self.v("τὸ παιδίον".split(), ["paidion", "to"]))


if __name__ == "__main__":
    unittest.main()
