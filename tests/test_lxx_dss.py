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
        bad = self.q("select count(*) n from verses where corpus='lxx' and "
                     "(ref not glob '*.[0-9]*.[0-9]*' or ref glob '*[a-z]')")["n"]
        self.assertEqual(bad, 0)

    def test_prov_25_29_unshifted(self):
        self.assertIsNone(self.text("lxx", "Rahlfs", "Prov.32.10"))
        t = self.text("lxx", "Rahlfs", "Prov.25.10")
        self.assertIsNotNone(t)
        self.assertEqual(self.q("select count(*) n from verses where corpus='lxx' and ref like 'Prov.3_.%'")["n"], 0)

    def test_daniel_3_additions_skipped(self):
        # Rahlfs Dan 3:24-90 (Prayer of Azariah / Song) have an A-book target: not canonical verses.
        # Rahlfs 3:91 is KJV 3:24.
        self.assertNotIn("προσηύξατο", self.text("lxx", "Rahlfs", "Dan.3.24") or "")  # Rahlfs 3:24 (addition)
        self.assertIsNone(self.text("lxx", "Rahlfs", "Dan.3.91"))
        self.assertIsNotNone(self.text("lxx", "Rahlfs", "Dan.3.24"))

    def test_ps_151_skipped(self):
        self.assertEqual(self.q("select count(*) n from verses where corpus='lxx' and ref like 'Ps.151.%'")["n"], 0)

    def test_jer_overrides(self):
        self.assertIn("ἐπιφανοῦμαι", self.text("lxx", "Rahlfs", "Jer.29.14"))
        self.assertIsNone(self.text("lxx", "Rahlfs", "Jer.36.14"))
        self.assertIn("Αιλαμ", self.text("lxx", "Rahlfs", "Jer.49.34"))
        self.assertNotIn("Σεδεκιου", self.text("lxx", "Rahlfs", "Jer.25.20") or "")
        # Rahlfs 38:35-37 are MT 31:37, 35, 36
        self.assertEqual(self.q("select count(*) n from verses where corpus='lxx' and ref in "
                                "('Jer.31.35','Jer.31.36','Jer.31.37')")["n"], 3)

    def test_deut_23_transposition(self):
        w = self.q("select text from verses where corpus='lxx' and ref='Deut.23.24'")["text"]
        src = self.q("select text from verses where corpus='lxx' and ref='Deut.23.25'")["text"]
        self.assertNotEqual(w, src)

    def test_one_to_many_follows_neighbour_offset(self):
        # Jonah 2: Rahlfs 2:6 feeds KJV 2:5 and 2:6; the previous source verse (2:5 -> 2:4) says it is 2:5.
        # Ezek 21: Rahlfs 21:26 ("διότι στήσεται ...") is KJV 21:21, not 21:26. Neither KJV verse may be empty.
        self.assertIsNotNone(self.text("lxx", "Rahlfs", "Jonah.2.5"))
        self.assertIsNotNone(self.text("lxx", "Rahlfs", "Jonah.2.4"))
        self.assertIn("στήσεται βασιλεὺς Βαβυλῶνος", self.text("lxx", "Rahlfs", "Ezek.21.21"))

    def test_one_to_many_picked_by_macula_greekstrong(self):
        # Jer 10: Rahlfs orders 10:4, 10:9, 10:5; Unbound sends 10:9 to KJV 10:5 or 10:9. The silver "from Tarshish"
        # is MT 10:9 (Jaccard 0.55 vs 0.13), so it must not be appended to 10:5 (the round-3 neighbour rule did that).
        self.assertIn("ἀπὸ Θαρσις", self.text("lxx", "Rahlfs", "Jer.10.9"))
        self.assertNotIn("Θαρσις", self.text("lxx", "Rahlfs", "Jer.10.5"))
        # Ezek 7: Rahlfs 7:3 ("ἥκει τὸ πέρας") is MT 7:6 "an end is come" (Jaccard 1.0 vs 0); position alone keeps it
        # on 7:3, where Rahlfs 7:7 ("νῦν τὸ πέρας πρὸς σέ ...") belongs. Rahlfs 7:10 stays on 7:10.
        self.assertEqual(self.text("lxx", "Rahlfs", "Ezek.7.6"), "ἥκει τὸ πέρας")
        self.assertTrue(self.text("lxx", "Rahlfs", "Ezek.7.3").startswith("νῦν τὸ πέρας πρὸς σέ"))
        self.assertIn("ἡ ῥάβδος ἤνθηκεν", self.text("lxx", "Rahlfs", "Ezek.7.10"))

    def test_pick_rules(self):
        from loaders.lxx import pick
        ts = ["Jer.10.5", "Jer.10.9"]
        # data wins when clearly better (>= MIN_SCORE and >= MARGIN above the runner-up)
        self.assertEqual(pick(ts, "Jer.10.9", 9, ["Jer.10.4"], ["Jer.10.5"], {"Jer.10.5": 0.6, "Jer.10.9": 0.1}), "Jer.10.5")
        # too close or too weak: neighbours disagree (10.5 vs 10.4) -> own ref
        self.assertEqual(pick(ts, "Jer.10.9", 9, ["Jer.10.4"], ["Jer.10.5"], {"Jer.10.5": 0.3, "Jer.10.9": 0.2}), "Jer.10.9")
        self.assertEqual(pick(ts, "Jer.10.9", 9, ["Jer.10.4"], ["Jer.10.5"], {"Jer.10.5": 0.2, "Jer.10.9": 0}), "Jer.10.9")
        # single-target neighbours agreeing on an offset beat the own ref
        self.assertEqual(pick(["Jonah.2.5", "Jonah.2.6"], "Jonah.2.6", 6, ["Jonah.2.4"], ["Jonah.2.6"]), "Jonah.2.5")
        # no neighbour hint and no own ref -> same verse number -> first
        self.assertEqual(pick(["Isa.3.21", "Isa.3.22"], "Isa.4.22", 22, None, None), "Isa.3.22")
        self.assertEqual(pick(["Isa.3.21", "Isa.3.23"], "Isa.4.22", 22, None, None), "Isa.3.21")

    def test_one_to_many_prefers_own_ref(self):
        # Rahlfs Isa 53:2, 53:3 each keep their own KJV verse (none is folded into the previous one)
        a, b = self.text("lxx", "Rahlfs", "Isa.53.2"), self.text("lxx", "Rahlfs", "Isa.53.3")
        self.assertTrue(a and b)
        self.assertNotIn(b.split()[0] + " " + b.split()[1], a)

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


REAL_DB = ROOT / "data" / "bible.db"
# LXX verses that exist in no Masoretic (WLC) verse: Josh 21:36-37 (KJV has them, WLC does not),
# LXX verse 0 of Lam 1 (the opening sentence) and Dan 5:0 (heading).
LXX_ONLY = {"Josh.21.36", "Josh.21.37", "Lam.0.1", "Dan.5.0"}


@unittest.skipUnless(REAL_DB.is_file(), "needs a real build (python3 scripts/build_db.py)")
class RealBuildRefSpace(unittest.TestCase):
    def test_lxx_refs_inside_kjv_ot_ref_space(self):
        import sqlite3
        c = sqlite3.connect(f"file:{REAL_DB}?mode=ro", uri=True)
        try:
            kjv = {r for (r,) in c.execute("select ref from verses where corpus='hebot' and witness='WLC'")}
            lxx = {r for (r,) in c.execute("select distinct ref from verses where corpus='lxx'")}
        finally:
            c.close()
        if not lxx:
            self.skipTest("real DB has no LXX yet")
        self.assertEqual(sorted(lxx - kjv - LXX_ONLY), [])


if __name__ == "__main__":
    unittest.main()
