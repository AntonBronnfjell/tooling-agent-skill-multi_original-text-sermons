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
    def test_range_same_chapter_repeated(self):
        self.assertEqual(to_osis(parse_ref("John.3.16-3.17")), "John.3.16-17")
        self.assertEqual(to_osis(parse_ref("Juan 3:16-3:17")), "John.3.16-17")
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

    def test_every_alias_resolves(self):
        from otslib.refs import _ALIASES
        for alias, book in _ALIASES.items():
            self.assertEqual(parse_ref(f"{alias} 1:1").book, book, alias)

    def test_spanish_full_names_all_66(self):
        names = """Génesis Éxodo Levítico Números Deuteronomio Josué Jueces Rut|1 Samuel|2 Samuel|1 Reyes|2 Reyes
        |1 Crónicas|2 Crónicas|Esdras|Nehemías|Ester|Job|Salmos|Proverbios|Eclesiastés|Cantares|Cantar de los Cantares
        |Isaías|Jeremías|Lamentaciones|Ezequiel|Daniel|Oseas|Joel|Amós|Abdías|Jonás|Miqueas|Nahúm|Habacuc|Sofonías|Hageo
        |Zacarías|Malaquías|Mateo|Marcos|Lucas|Juan|Hechos|Romanos|1 Corintios|2 Corintios|Gálatas|Efesios|Filipenses
        |Colosenses|1 Tesalonicenses|2 Tesalonicenses|1 Timoteo|2 Timoteo|Tito|Filemón|Hebreos|Santiago|1 Pedro|2 Pedro
        |1 Juan|2 Juan|3 Juan|Judas|Apocalipsis""".replace("\n", "")
        singles = "Génesis Éxodo Levítico Números Deuteronomio Josué Jueces Rut".split()
        rest = [n.strip() for n in names.split("|")][1:]
        full = singles + rest
        seen = {parse_ref(f"{n} 1:1").book for n in full}
        self.assertEqual(seen, set(BOOKS))

    def test_spanish_abbreviations(self):
        cases = {"Jr": "Jer", "Lm": "Lam", "Sl": "Ps", "1 P": "1Pet", "2 P": "2Pet", "1 Tm": "1Tim",
                 "2 Tm": "2Tim", "Hb": "Heb", "Jds": "Jude", "Ct": "Song", "Qo": "Eccl", "1 R": "1Kgs",
                 "2 R": "2Kgs", "1 S": "1Sam", "2 S": "2Sam", "St": "Jas", "Mc": "Mark", "Mic": "Mic",
                 "Miq": "Mic"}
        for ab, book in cases.items():
            self.assertEqual(parse_ref(f"{ab} 1:1").book, book, ab)

    def test_mc_is_mark(self): self.assertEqual(to_osis(parse_ref("Mc 1:1")), "Mark.1.1")
    def test_roman_prefix(self): self.assertEqual(to_osis(parse_ref("I Juan 5:7")), "1John.5.7")
    def test_roman_prefix_iii(self): self.assertEqual(to_osis(parse_ref("III Jn 1:4")), "3John.1.4")
    def test_primera_de(self): self.assertEqual(to_osis(parse_ref("Primera de Juan 5:7")), "1John.5.7")
    def test_isaiah_not_roman(self): self.assertEqual(to_osis(parse_ref("Isaías 53:5")), "Isa.53.5")


if __name__ == "__main__":
    unittest.main()
