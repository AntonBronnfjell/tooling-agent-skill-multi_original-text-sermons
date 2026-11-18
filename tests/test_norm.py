import os
import sys
import unittest

# `discover -s tests` does not import tests/__init__.py, so repeat the path setup.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from otslib.norm import display, match_key, nfc, strip_accents


class NormTests(unittest.TestCase):
    def test_hebrew_cantillation_removed(self):
        self.assertEqual(display("בְּרֵאשִׁ֖ית", "heb"), "בְּרֵאשִׁית")
    def test_greek_match_key(self):
        self.assertEqual(match_key("Καὶ θεὸς ἦν ὁ λόγος.", "grc"), match_key("καὶ θεὸς ἦν ὁ λόγος", "grc"))
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
