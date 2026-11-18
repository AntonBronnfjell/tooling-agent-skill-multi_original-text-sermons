import os
import sys
import unittest

# `discover -s tests` does not import tests/__init__.py, so repeat the path setup.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from otslib.refs import BOOKS, RefError, parse_ref, to_osis


class RefTests(unittest.TestCase):
    def test_osis(self): self.assertEqual(to_osis(parse_ref("John.3.16")), "John.3.16")
    def test_spanish(self): self.assertEqual(to_osis(parse_ref("Juan 3:16")), "John.3.16")
    def test_abbrev(self): self.assertEqual(to_osis(parse_ref("1 Jn 5:7")), "1John.5.7")
    def test_abbrev_nospace(self): self.assertEqual(to_osis(parse_ref("1Jn 5:7")), "1John.5.7")
    def test_spanish_numbered(self): self.assertEqual(to_osis(parse_ref("1 Juan 5:7")), "1John.5.7")
    def test_chapter_only(self): self.assertEqual(to_osis(parse_ref("Jn 3")), "John.3")
    def test_range(self): self.assertEqual(to_osis(parse_ref("Juan 3:16-17")), "John.3.16-17")
    def test_psalms_es(self): self.assertEqual(to_osis(parse_ref("Salmos 51:1")), "Ps.51.1")
    def test_matthew_es(self): self.assertEqual(to_osis(parse_ref("Mateo 16:18")), "Matt.16.18")
    def test_accent_case(self): self.assertEqual(to_osis(parse_ref("GÉNESIS 1:1")), "Gen.1.1")
    def test_accent_missing(self): self.assertEqual(to_osis(parse_ref("exodo 3:14")), "Exod.3.14")
    def test_song_es(self): self.assertEqual(to_osis(parse_ref("Cantares 2:1")), "Song.2.1")
    def test_song_es_long(self): self.assertEqual(to_osis(parse_ref("Cantar de los Cantares 2:1")), "Song.2.1")
    def test_revelation(self): self.assertEqual(to_osis(parse_ref("Apocalipsis 21:4")), "Rev.21.4")
    def test_sbl(self): self.assertEqual(to_osis(parse_ref("Phlm 1:6")), "Phlm.1.6")
    def test_english_full(self): self.assertEqual(to_osis(parse_ref("Song of Solomon 2:1")), "Song.2.1")
    def test_unknown(self):
        with self.assertRaises(RefError): parse_ref("Hezekiah 1:1")
    def test_garbage(self):
        with self.assertRaises(RefError): parse_ref("John")

    def test_books(self):
        self.assertEqual(len(BOOKS), 66)
        self.assertEqual(BOOKS[0], "Gen")
        self.assertEqual(BOOKS[-1], "Rev")

    def test_every_book_roundtrips_names(self):
        for b in BOOKS:
            self.assertEqual(parse_ref(f"{b}.1.1").book, b)


if __name__ == "__main__":
    unittest.main()
