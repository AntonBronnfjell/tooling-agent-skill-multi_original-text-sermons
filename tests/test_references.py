import os
import sys
import unittest

# `discover -s tests` does not import tests/__init__.py, so repeat the path setup.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from otslib.references import contested_refs, template_sections, tradition_terms

REQUIRED_CONTESTED = {"John.1.1", "Gal.2.16", "Gen.1.26", "Acts.2.38", "1John.5.7", "Matt.28.19",
                      "Isa.9.6", "Phil.2.6", "Titus.2.13", "Rom.9.5", "Col.2.9", "Deut.6.4"}


class ReferenceTableTests(unittest.TestCase):
    def test_tables_parse(self):
        self.assertGreaterEqual(len(tradition_terms("en")), 20)
        self.assertGreaterEqual(len(tradition_terms("es")), 20)
        self.assertIn("John.1.1", contested_refs())

    def test_terms_lowercase_and_known(self):
        self.assertIn("church", tradition_terms("en"))
        self.assertIn("iglesia", tradition_terms("es"))
        self.assertIn("holy ghost", tradition_terms("en"))
        self.assertTrue(all(t == t.lower() for t in tradition_terms("es")))

    def test_unknown_lang_empty(self):
        self.assertEqual(tradition_terms("xx"), set())

    def test_contested_required(self):
        self.assertTrue(REQUIRED_CONTESTED <= contested_refs())

    def test_contested_refs_are_osis(self):
        from otslib.refs import parse_ref, to_osis
        for r in contested_refs():
            self.assertEqual(to_osis(parse_ref(r)), r)

    def test_template_sections(self):
        self.assertEqual(template_sections("hook-book-look-took"), ["Hook", "Book", "Look", "Took", "Notes"])
        self.assertEqual(template_sections("big-idea"),
                         ["Introduction", "Text", "Big Idea", "Point 1", "Point 2", "Point 3", "Conclusion", "Notes"])

    def test_template_unknown(self):
        with self.assertRaises(FileNotFoundError):
            template_sections("no-such-template")


if __name__ == "__main__":
    unittest.main()
