import os
import sys
import unittest

# `discover -s tests` does not import tests/__init__.py, so repeat the path setup.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from otslib.norm import display, match_key, nfc, strip_accents, strip_points


class NormTests(unittest.TestCase):
    def test_hebrew_cantillation_removed(self):
        self.assertEqual(display("בְּרֵאשִׁ֖ית", "heb"), "בְּרֵאשִׁית")
    def test_greek_match_key(self):
        self.assertEqual(match_key("Καὶ θεὸς ἦν ὁ λόγος.", "grc"), match_key("καὶ θεὸς ἦν ὁ λόγος", "grc"))
    def test_greek_elision_marks_fold(self):
        k = match_key("δι\u2019 οὗ", "grc")
        self.assertEqual(k, match_key("δι\u1fbd οὗ", "grc"))
        self.assertEqual(k, match_key("δι' οὗ", "grc"))
        self.assertEqual(k, match_key("δι\u02bc οὗ", "grc"))
        self.assertEqual(display("δι\u2019 οὗ", "grc"), "δι\u2019 οὗ")  # display keeps the source mark
    def test_greek_psili_elision_folds(self):
        self.assertEqual(match_key("ἀλλ\u1fbf ἵνα", "grc"), match_key("ἀλλ\u2019 ἵνα", "grc"))
    def test_editorial_brackets_stripped(self):
        self.assertEqual(match_key("[[καὶ]] ⟦θεὸς⟧ [ἦν]", "grc"), match_key("καὶ θεὸς ἦν", "grc"))
        self.assertEqual(match_key("ב[ר]אשית", "heb"), match_key("בראשית", "heb"))
    def test_strip_points(self):
        self.assertEqual(strip_points("בְּרֵאשִׁית"), "בראשית")
    def test_greek_grave_folds_to_acute(self):
        self.assertEqual(match_key("καὶ θεὸς", "grc"), match_key("καί θεός", "grc"))
        self.assertNotEqual(match_key("καὶ", "grc"), match_key("και", "grc"))  # accent still required
    def test_maqaf(self):
        self.assertEqual(match_key("כָּל־הָאָרֶץ", "heb"), match_key("כָּל הָאָרֶץ", "heb"))
    def test_greek_display_unchanged(self):
        self.assertEqual(display("Καὶ θεὸς", "grc"), "Καὶ θεὸς")
    def test_hebrew_vowels_kept_meteg_removed(self):
        self.assertEqual(display("אָֽ", "heb"), "אָ")
    def test_match_key_punct(self):
        self.assertEqual(match_key("הָאָרֶץ׃ ", "heb"), match_key("הָאָרֶץ", "heb"))
    def test_nfc(self):
        self.assertEqual(nfc("é"), "é")
    def test_strip_accents(self):
        self.assertEqual(strip_accents("Καὶ"), "Και")
