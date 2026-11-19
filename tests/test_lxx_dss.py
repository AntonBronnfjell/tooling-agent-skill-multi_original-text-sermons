import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from otslib.tf import read_feature, read_oslots  # noqa: E402
from test_build_stepbible import FIXTURES, build  # noqa: E402

TF = ROOT / "tests" / "fixtures" / "tf"


class TextFabric(unittest.TestCase):
    def test_tf_range_line(self):
        f = read_feature(TF / "range.tf")
        self.assertEqual(f[3], "x")
        self.assertEqual(f[1], "x")

    def test_tf_implicit_increment_and_lists(self):
        f = read_feature(TF / "range.tf")
        self.assertEqual(f[7], "y")
        self.assertEqual(f[8], "z")  # bare value line: previous node + 1
        self.assertEqual((f[4], f[6]), ("w", "w"))

    def test_oslots(self):
        o = read_oslots(TF / "oslots.tf")
        self.assertEqual(o[1], [1, 2, 3, 5])
        self.assertEqual(o[2], [4])  # bare slotspec line: previous node + 1

    def test_oslots_filter(self):
        self.assertEqual(list(read_oslots(TF / "oslots.tf", nodes={2})), [2])


class Loaded(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"),
                         only=("stepbible", "versification", "macula", "lxx", "dss"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def text(self, corpus, witness, ref):
        r = self.q("select text from verses where corpus=? and witness=? and ref=?", corpus, witness, ref)
        return r["text"] if r else None


class Lxx(Loaded):
    def test_lxx_isa_45_23_theo(self):
        self.assertIn("θεῷ", self.text("lxx", "Rahlfs", "Isa.45.23"))

    def test_lxx_ps_mapped(self):
        self.assertIsNotNone(self.q("select 1 from verses where corpus='lxx' and ref='Ps.51.1'"))

    def test_ps_title_merged_into_verse_0(self):
        # LXX Ps 50:1-2 (title) both map to canonical Ps 51:0: one verse, both parts
        self.assertEqual(self.q("select count(*) n from verses where corpus='lxx' and ref='Ps.51.0'")["n"], 1)

    def test_exod_20_order_mapped(self):
        # Rahlfs Exod 20:15 is the commandment KJV numbers 20:13
        self.assertIn("φονεύσεις", self.text("lxx", "Rahlfs", "Exod.20.13"))

    def test_jer_mapped(self):
        # Rahlfs Jer 26:2 (Egypt oracle) is KJV Jer 46:2
        self.assertIsNone(self.text("lxx", "Rahlfs", "Jer.26.2"))
        self.assertIsNotNone(self.text("lxx", "Rahlfs", "Jer.46.2"))

    def test_word_fields(self):
        r = self.q("select * from words where corpus='lxx' and ref='Gen.1.1' and pos=1")
        self.assertEqual((r["witness"], r["surface"], r["lemma"], r["strongs"]), ("Rahlfs", "ἐν", "ἐν", "G1722"))
        self.assertTrue(r["morph"])

    def test_match_key_set(self):
        r = self.q("select match_key from verses where corpus='lxx' and ref='Gen.1.1'")
        self.assertTrue(r["match_key"])

    def test_neh_shifted_to_kjv(self):
        self.assertIsNotNone(self.text("lxx", "Rahlfs", "Neh.1.1"))
        self.assertIsNone(self.text("lxx", "Rahlfs", "Neh.11.1"))

    def test_malachi_ch4_from_unbound_map(self):
        self.assertIsNone(self.text("lxx", "Rahlfs", "Mal.3.22"))
        for v in (4, 5, 6):
            self.assertIsNotNone(self.text("lxx", "Rahlfs", f"Mal.4.{v}"))

    def test_lettered_refs_folded_into_base_verse(self):
        n = self.q("select count(*) n from verses where corpus='lxx' and ref glob '*[a-z]'")["n"]
        self.assertEqual(n, 0)
        r = self.q("select count(*) n from words where corpus='lxx' and ref='Exod.28.29'")["n"]
        self.assertGreater(r, 3)

    def test_collisions_concatenated_in_source_order(self):
        # Rahlfs Ps 50:1 (6 words) and 50:2 (12 words) both land on Ps.51.0: one verse, source order kept
        n = self.q("select count(*) n from words where corpus='lxx' and ref='Ps.51.0'")["n"]
        self.assertEqual(n, 18)
        first = self.q("select surface from words where corpus='lxx' and ref='Ps.51.0' and pos=1")["surface"]
        self.assertTrue(self.text("lxx", "Rahlfs", "Ps.51.0").startswith(first))

    def test_all_lxx_refs_canonical_shape(self):
        bad = self.q("select count(*) n from verses where corpus='lxx' and ref not glob '*.[0-9]*.[0-9]*' or ref glob '*[a-z]'")["n"]
        self.assertEqual(bad, 0)

    def test_oslots_skip(self):
        # only Rahlfs witness in the fixture (no double-text books)
        self.assertEqual(self.q("select count(distinct witness) n from verses where corpus='lxx'")["n"], 1)


class Dss(Loaded):
    def test_dss_1qisaa(self):
        self.assertIsNotNone(self.q("select 1 from verses where corpus='dss' and witness='1QIsaa' and ref='Isa.53.11'"))

    def test_1qisaa_has_or(self):
        self.assertIn("אור", self.text("dss", "1QIsaa", "Isa.53.11"))

    def test_proclitics_joined_via_after(self):
        t = self.text("dss", "1QIsaa", "Isa.53.11")
        for w in ("מעמל", "וישבע", "ובדעתו", "לרבים"):
            self.assertIn(w, t)
        self.assertNotIn("  ", t)

    def test_4q58_reconstructed_resh_absent_from_verse(self):
        t = self.text("dss", "4Q58", "Isa.53.11")
        self.assertIsNotNone(t)
        self.assertNotIn("אור", t)
        self.assertIn("או ", t)
        self.assertIn("שבע", t)

    def test_4q58_word_surface_brackets_and_flags(self):
        rows = self.conn.execute("select surface, editions from words where corpus='dss' and witness='4Q58' "
                                 "and ref='Isa.53.11'").fetchall()
        hit = [r for r in rows if r["surface"] == "או[ר]"]
        self.assertTrue(hit)
        self.assertIn("rec", hit[0]["editions"])

    def test_removed_letters_dropped(self):
        t = self.text("dss", "1QIsaa", "Isa.53.9")
        self.assertIn("עשיר", t)
        self.assertNotIn("עשירים", t)
        r = self.q("select surface, editions from words where corpus='dss' and witness='1QIsaa' "
                   "and ref='Isa.53.9' and surface like 'עשיר%'")
        self.assertEqual(r["surface"], "עשיר")
        self.assertIn("rem", r["editions"])

    def test_other_witnesses_present(self):
        ws = {r[0] for r in self.conn.execute("select distinct witness from verses where corpus='dss'")}
        self.assertTrue({"1QIsaa", "1Q8", "4Q56", "4Q58"} <= ws)

    def test_no_morpheme_separator_in_text(self):
        t = self.text("dss", "1QIsaa", "Isa.53.9")
        self.assertNotIn("׳", t)

    def test_word_lemma_homonym_suffix_stripped(self):
        self.assertEqual(self.q("select count(*) n from words where corpus='dss' and lemma like '%\\_%' escape '\\'")["n"], 0)


if __name__ == "__main__":
    unittest.main()
