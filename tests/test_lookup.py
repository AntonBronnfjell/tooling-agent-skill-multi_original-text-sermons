import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_build_stepbible import FIXTURES  # noqa: E402
import build_db  # noqa: E402,F401  (path set by test_build_stepbible)
import io  # noqa: E402

LOOKUP = ROOT / "scripts" / "lookup.py"


def run_raw(*args, db=None):
    env = {**os.environ, "OTS_DB": db or Lookup.db}
    return subprocess.run([sys.executable, str(LOOKUP), *args], capture_output=True, text=True, env=env)


def run(*args):
    r = run_raw(*args)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Lookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.db = os.path.join(cls.tmp, "t.db")
        build_db.build(Path(FIXTURES), Path(cls.db), out=io.StringIO())
        Lookup.db = cls.db
        import sqlite3
        c = sqlite3.connect(cls.db)
        c.executemany("INSERT INTO lexicon VALUES (?,?,?,?,?)", [
            ("G2010", "ἐπιτρέπω", "grc", "permit", ""), ("G20100", "ἄλλο", "grc", "other", ""),
            ("G14730", "ἄλλο2", "grc", "other2", "")])  # fixture already has G1473, G2424*, G2532
        c.execute("INSERT INTO variants VALUES ('Acts.2.4', 9, 'zzz', 'Byz+KJV')")
        c.executemany("INSERT INTO variants VALUES (?,?,?,?)", [
            ("Acts.2.4", 10, "yyy", "Byz+02"), ("Acts.2.4", 11, "xxx", "NIV+01")])
        # real shapes: TAGNT row tagged for a witness that spells the word differently (variants row)
        alled = "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz"
        for ref, pos, surf, lem, txt_w, txt in [
                ("1Cor.10.2", 5, "Μωϋσῆν", "Μωϋσῆς", "TR", "καὶ πάντες εἰς τὸν Μωσῆν ἐβαπτίσαντο"),
                ("1Cor.1.17", 7, "ἀλλ᾽", "ἀλλά", "SBL", "οὐκ ἐν σοφίᾳ λόγου Χριστὸς ἀλλὰ ἐν")]:
            c.execute("INSERT INTO words VALUES ('grnt','TAGNT',?,?,?,?,'G0001','N','g',?,'','')", (ref, pos, surf, lem, alled))
            c.execute("INSERT INTO verses VALUES ('grnt',?,?,?,'')", (txt_w, ref, txt))
        c.execute("INSERT INTO variants VALUES ('1Cor.10.2', 5, 'Μωσῆν', 'TR')")
        c.execute("INSERT INTO variants VALUES ('1Cor.1.17', 7, 'ἀλλὰ', 'NA27+Tyn+SBL+WH+Treg+TR+Byz')")
        c.commit()
        c.close()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_verse_json(self):
        self.assertEqual(run("verse", "Juan 1:1")["ref"], "John.1.1")

    def test_verse_words_for_witness_and_default(self):
        o = run("verse", "John.1.1")
        self.assertEqual((o["corpus"], o["witness"]), ("grnt", "SBL"))
        self.assertIn("λόγος", o["text"])
        self.assertEqual(o["words"][0]["surface"], "Ἐν")
        self.assertEqual(set(o["words"][0]), {"pos", "surface", "lemma", "strongs", "morph", "gloss", "domain", "syntax_role"})

    def test_ot_defaults_to_hebot(self):
        o = run("verse", "Gen.1.1")
        self.assertEqual((o["corpus"], o["witness"]), ("hebot", "WLC"))

    def test_absent_witness(self):
        out = run("verse", "Acts.8.37", "--witness", "SBL")
        self.assertEqual(out["absent_in"], "SBL")
        self.assertIn("TR", out["present_in"])

    def test_edition_word_filter(self):
        tr = run("verse", "Acts.2.4", "--witness", "TR")["words"]
        sbl = run("verse", "Acts.2.4", "--witness", "SBL")["words"]
        self.assertNotIn("πάντες", [w["surface"] for w in tr])  # TR reads ἅπαντες there
        self.assertIn("πάντες", [w["surface"] for w in sbl])

    def test_dss_verse_flags_and_extant_only(self):
        o = run("verse", "Isa.53.11", "--corpus", "dss", "--witness", "4Q56")
        self.assertTrue(o["extant_only"])
        self.assertIn("reconstructed", o["note"])
        self.assertIn("rec", o["words"][0]["flags"])

    def test_dss_requires_witness(self):
        self.assertEqual(run_raw("verse", "Isa.53.11", "--corpus", "dss").returncode, 1)

    def test_ext_raw_ref_bracketed(self):
        o = run("verse", "Ant.18.63", "--corpus", "ext", "--witness", "Josephus")
        self.assertEqual(o["ref"], "Ant.18.63")
        self.assertTrue(o["editor_bracketed"])
        self.assertTrue(o["words"][0]["editor_bracketed"])

    def test_interlinear(self):
        w = run("interlinear", "John.1.1")["words"]
        self.assertEqual(set(w[0]), {"pos", "surface", "gloss"})

    def test_comma_variant_late(self):
        self.assertTrue(any(v["class"] == "late" for v in run("variants", "1John.5.7")))

    def test_variant_early_when_not_only_tr_byz(self):
        v = run("variants", "Acts.2.4")
        self.assertIn(("πάντες", "early"), [(x["reading"], x["class"]) for x in v])
        self.assertIn(("ἅπαντες", "late"), [(x["reading"], x["class"]) for x in v])

    def test_variants_displaced_suffix_is_late(self):
        v = run("variants", "Acts.2.38")
        self.assertTrue(all(x["class"] == "late" for x in v if x["editions"].startswith("TR")))

    def test_late_ignores_translation_tokens(self):
        v = [x for x in run("variants", "Acts.2.4") if x["reading"] == "zzz"]
        self.assertEqual(v[0]["class"], "late")

    def test_strongs_no_prefix_collision(self):
        self.assertEqual({r["lemma"] for r in run("word", "G2010")["lexicon"]}, {"ἐπιτρέπω"})
        self.assertEqual({r["strongs"] for r in run("word", "G1473")["lexicon"]}, {"G1473"})
        self.assertEqual(run("search", "G2010")["lemmas"], ["ἐπιτρέπω"])

    def test_strongs_suffix_and_combined(self):
        self.assertEqual([r["strongs"] for r in run("word", "G2424I")["lexicon"]], ["G2424I"])
        self.assertEqual({r["strongs"] for r in run("word", "G2424")["lexicon"]},
                         {"G2424G", "G2424H", "G2424I", "G2424J", "G2424K"})
        self.assertEqual({r["strongs"] for r in run("word", "G1473+G2532")["lexicon"]}, {"G1473", "G2532"})

    def test_variant_reading_merged_into_words(self):
        o = run("verse", "Acts.2.4", "--witness", "TR")
        w = [x for x in o["words"] if x["surface"] == "ἅπαντες"]
        self.assertEqual(len(w), 1)
        self.assertTrue(w[0]["from_variant"])
        self.assertEqual(w[0]["pos"], 3)
        self.assertEqual([x["pos"] for x in o["words"]], sorted(x["pos"] for x in o["words"]))

    def test_variant_spelling_replaces_row_not_duplicates(self):
        for ref, wit, want in (("1Cor.10.2", "TR", "Μωσῆν"), ("1Cor.1.17", "SBL", "ἀλλὰ")):
            o = run("verse", ref, "--witness", wit)
            poss = [w["pos"] for w in o["words"]]
            self.assertEqual(len(poss), len(set(poss)))
            w = [x for x in o["words"] if x["surface"] == want]
            self.assertEqual(len(w), 1)
            self.assertTrue(w[0]["surface_from_variant"])
            self.assertTrue(w[0]["lemma"])  # lemma/morph kept
            self.assertIn(want, o["text"])

    def test_late_manuscript_sigla_are_early(self):
        cls = {x["reading"]: x["class"] for x in run("variants", "Acts.2.4")}
        self.assertEqual(cls["yyy"], "early")  # Byz+02
        self.assertEqual(cls["xxx"], "early")  # NIV+01
        self.assertEqual(cls["zzz"], "late")   # Byz+KJV

    def test_words_note_when_incomplete(self):
        self.assertIn("words_note", run("verse", "Mark.16.9", "--witness", "SBL"))
        self.assertIn("words_note", run("verse", "Ps.51.2", "--witness", "Ketiv"))
        self.assertNotIn("words_note", run("verse", "John.1.1"))

    def test_lxx_diff_base_key(self):
        self.assertEqual(run("lxx", "Isa.45.23")["base_witness"], "Rahlfs")
        o = run("dss", "Isa.53.11")
        self.assertEqual(o["base_witness"], "WLC")
        d = o["readings"][0]["diff_vs_hebot"][0]
        self.assertIn("base", d)
        self.assertNotIn("hebot", d)

    def test_compare(self):
        o = run("compare", "John.1.1")
        self.assertIn("KJV", o["versions"])
        self.assertIn("λόγος", o["original"])

    def test_compare_versions_filter(self):
        self.assertEqual(list(run("compare", "John.1.1", "--versions", "kjv,RV1909")["versions"]), ["KJV", "RV1909"])

    def test_usage_ext_matches_surface_forms(self):
        # fixture ext has no ἐκκλησία; δέ exercises the same accent-stripped surface path
        o = run("usage", "δέ")
        self.assertGreater(o["counts"]["ext"]["Josephus"], 0)
        self.assertLessEqual(len(o["contexts"]["ext"]["Josephus"]), 5)
        self.assertTrue(o["contexts"]["ext"]["Josephus"][0]["ref"])

    def test_usage_ext_split_by_witness(self):
        o = run("usage", "καί")
        self.assertEqual(set(o["counts"]["ext"]), {"Josephus", "Philo"})
        self.assertGreater(o["counts"]["ext"]["Philo"], 0)
        self.assertTrue(all(c["witness"] == "Philo" for c in o["contexts"]["ext"]["Philo"]))
        self.assertIn("ext:Philo", run_raw("usage", "καί", "--format", "text").stdout)

    def test_search_ext(self):
        o = run("search", "καί", "--corpus", "ext")
        r = o["results"]["ext"]
        self.assertGreater(r["occurrences"], 0)
        self.assertTrue(any(x.startswith("Philo ") for x in r["refs"]))
        self.assertTrue(any(x.startswith("Josephus ") for x in r["refs"]))
        self.assertIn("surface", o["results"]["ext"]["note"])

    def test_corpus_lacks_existing_verse(self):
        r = run_raw("dss", "Gen.1.1")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        self.assertEqual(o["readings"], [])
        self.assertEqual(o["absent"], "no DSS witness has Gen.1.1")
        t = run_raw("dss", "Gen.1.1", "--format", "text")
        self.assertIn("no DSS witness has Gen.1.1", t.stdout)
        v = run("verse", "Gen.1.1", "--corpus", "dss", "--witness", "1QIsaa")
        self.assertEqual(v["absent"], "no DSS witness has Gen.1.1")

    def test_unknown_ref_still_exit_1(self):
        for args in (("dss", "Gen.99.1"), ("lxx", "Hezekiah 1:1")):
            r = run_raw(*args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("unknown ref", r.stderr)

    def test_usage_papyri_labelled_ocr(self):
        o = run("usage", "ἐκκλησία")
        self.assertEqual(o["papyri_quality"], "noisy-ocr")
        self.assertIn("OCR", o["papyri"][0]["label"])

    def test_usage_papyri_null_when_absent(self):
        self.assertIsNone(run("usage", "λόγος")["papyri"])

    def test_word(self):
        o = run("word", "λόγος")
        self.assertEqual(o["lexicon"][0]["strongs"], "G3056")
        self.assertIn("co-occurrence", o["lxx_hebrew_cooccurrence_note"])
        self.assertEqual(run("word", "G3056")["lexicon"][0]["lemma"], "λόγος")

    def test_dss_diff(self):
        o = run("dss", "Isa.53.11")
        self.assertTrue(o["readings"])
        r = {x["witness"]: x for x in o["readings"]}
        self.assertTrue(r["1QIsaa"]["extant_only"])
        self.assertFalse(r["1QIsaa"]["identical_to_wlc"])
        self.assertIn("אור", sum([d["reading"] for d in r["1QIsaa"]["diff_vs_hebot"]], []))

    def test_lxx(self):
        o = run("lxx", "Isa.45.23")
        self.assertEqual(o["readings"][0]["witness"], "Rahlfs")

    def test_search(self):
        o = run("search", "λόγος", "--corpus", "grnt")
        self.assertIn("John.1.1", o["results"]["grnt"]["refs"])

    def test_text_format(self):
        r = run_raw("verse", "John.1.1", "--format", "text")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.startswith("John.1.1 [grnt:SBL]"))

    def test_unknown_ref_exit_1(self):
        r = run_raw("verse", "Hezekiah 1:1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown ref", r.stderr)

    def test_missing_db_exit_2(self):
        r = run_raw("verse", "John.1.1", db="/nonexistent.db")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
