import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from otslib.refs import canonical, source_ref  # noqa: E402
from test_build_stepbible import FIXTURES, build  # noqa: E402


class Versification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.c = build(FIXTURES, os.path.join(cls.tmp, "t.db"), only=("stepbible", "versification"))

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        shutil.rmtree(cls.tmp)

    def test_mal(self):
        self.assertEqual(canonical(self.c, "hebrew", "Mal.3.19"), "Mal.4.1")

    def test_ps51_hebrew(self):
        self.assertEqual(canonical(self.c, "hebrew", "Ps.51.3"), "Ps.51.1")

    def test_ps51_lxx(self):
        self.assertEqual(canonical(self.c, "lxx", "Ps.50.3"), "Ps.51.1")

    def test_lxx_mal(self):
        self.assertEqual(canonical(self.c, "lxx", "Mal.3.19"), "Mal.4.1")

    def test_title_is_verse_zero(self):
        self.assertEqual(canonical(self.c, "lxx", "Ps.50.1"), "Ps.51.0")

    def test_lxx_starred_rows(self):
        self.assertEqual(canonical(self.c, "lxx", "Jer.32.1"), "Jer.25.15")
        self.assertEqual(canonical(self.c, "lxx", "Jer.26.2"), "Jer.46.2")
        self.assertEqual(canonical(self.c, "lxx", "Exod.20.15"), "Exod.20.13")

    def test_hebrew_multi_verse_cell(self):
        self.assertEqual(canonical(self.c, "hebrew", "Ps.52.1"), "Ps.52.0")
        self.assertEqual(canonical(self.c, "hebrew", "Ps.52.2"), "Ps.52.0")

    def test_identity(self):
        self.assertEqual(canonical(self.c, "lxx", "Gen.1.1"), "Gen.1.1")
        self.assertEqual(canonical(self.c, "hebrew", "Gen.1.1"), "Gen.1.1")

    def test_source_ref_inverse(self):
        self.assertEqual(source_ref(self.c, "hebrew", "Mal.4.1"), "Mal.3.19")
        self.assertEqual(source_ref(self.c, "lxx", "Ps.51.1"), "Ps.50.3")
        self.assertEqual(source_ref(self.c, "lxx", "Gen.1.1"), "Gen.1.1")

    def test_tahot_stored_english(self):
        self.assertIsNotNone(self.c.execute(
            "select 1 from verses where corpus='hebot' and ref='Mal.4.1'").fetchone())


if __name__ == "__main__":
    unittest.main()
