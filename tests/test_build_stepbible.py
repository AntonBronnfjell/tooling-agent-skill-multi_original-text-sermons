import io
import lzma
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_db  # noqa: E402
from otslib import db  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "sources"

TAHOT_HDR = ("Eng (Heb) Ref & Type\tHebrew\tTransliteration\tTranslation\tdStrongs\tGrammar\t"
             "Meaning Variants\tSpelling Variants\tRoot dStrong+Instance\tAlternative Strongs+Instance\t"
             "Conjoin word\tExpanded Strong tags")


def tahot_row(ref, heb, root="H0001A", kmean="", kspell="", tag="{H0001A=אב=father}"):
    return "\t".join([ref, heb, "tr", "gloss", "{" + root + "}", "HNcmsa", kmean, kspell, root, "", "", tag, "", "", "", "", ""])


def write_xz(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with lzma.open(path, "wt", encoding="utf-8") as f:
        f.write(text)


def build(sources, dest, only=("stepbible",)):
    build_db.build(Path(sources), Path(dest), only=list(only), out=io.StringIO())
    conn = sqlite3.connect(dest)
    conn.row_factory = sqlite3.Row
    return conn


class FixtureBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.conn = build(FIXTURES, os.path.join(cls.tmp, "t.db"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def q(self, sql, *args):
        return self.conn.execute(sql, args).fetchone()

    def test_sbl_john_1_1(self):
        row = self.q("select text from verses where corpus='grnt' and witness='SBL' and ref='John.1.1'")
        self.assertIn("θεὸς ἦν ὁ λόγος", row["text"])

    def test_acts_8_37_absent_in_sbl_present_in_tr(self):
        self.assertIsNone(self.q("select 1 from verses where corpus='grnt' and witness='SBL' and ref='Acts.8.37'"))
        self.assertIsNotNone(self.q("select 1 from verses where corpus='grnt' and witness='TR' and ref='Acts.8.37'"))

    def test_comma_only_late(self):
        sbl = self.q("select text from verses where corpus='grnt' and witness='SBL' and ref='1John.5.7'")["text"]
        self.assertNotIn("πατήρ", sbl)
        tr = self.q("select text from verses where corpus='grnt' and witness='TR' and ref='1John.5.7'")["text"]
        self.assertIn("πατήρ", tr)

    def test_hebrew_display_no_cantillation(self):
        t = self.q("select text from verses where corpus='hebot' and witness='WLC' and ref='Gen.1.1'")["text"]
        self.assertFalse(any(0x0591 <= ord(c) <= 0x05AF for c in t))
        self.assertTrue(t)

    def test_hebrew_no_morpheme_separators(self):
        for r in self.conn.execute("select text from verses where corpus='hebot'"):
            self.assertNotIn("/", r["text"])
            self.assertNotIn("\\", r["text"])

    def test_hebrew_maqaf_joins_next_word(self):
        t = self.q("select text from verses where corpus='hebot' and witness='WLC' and ref='Mal.4.1'")["text"]
        self.assertNotIn("־ ", t)
        self.assertIn("־", t)

    def test_psalm_title_and_english_numbering(self):
        self.assertIsNotNone(self.q("select 1 from verses where corpus='hebot' and ref='Ps.51.0'"))
        self.assertIsNotNone(self.q("select 1 from verses where corpus='hebot' and ref='Ps.51.1'"))

    def test_ketiv_witness_only_where_it_differs(self):
        k = self.q("select text from verses where corpus='hebot' and witness='Ketiv' and ref='Ps.51.2'")["text"]
        self.assertIn("הַרְבֵּה", k)
        w = self.q("select text from verses where corpus='hebot' and witness='WLC' and ref='Ps.51.2'")["text"]
        self.assertNotIn("הַרְבֵּה", w)
        self.assertIsNone(self.q("select 1 from verses where witness='Ketiv' and ref='Gen.1.1'"))

    def test_greek_surface_clean(self):
        for r in self.conn.execute("select text from verses where corpus='grnt'"):
            self.assertNotIn("(", r["text"])
            self.assertNotIn("¶", r["text"])
        w = self.q("select surface from words where corpus='grnt' and ref='John.1.1' and pos=1")
        self.assertEqual(w["surface"], "Ἐν")

    def test_tr_byz_substituted_readings(self):
        tr = self.q("select text from verses where corpus='grnt' and witness='TR' and ref='Acts.2.38'")["text"]
        self.assertIn("ἔφη", tr)
        self.assertNotIn("φησὶν", tr)
        self.assertIn("λήψεσθε", tr)
        thgnt = self.q("select text from verses where corpus='grnt' and witness='THGNT' and ref='Acts.2.38'")["text"]
        self.assertIn("φησὶν", thgnt)
        self.assertIn("λήμψεσθε", thgnt)
        wh = self.q("select text from verses where corpus='grnt' and witness='WH' and ref='Acts.2.38'")["text"]
        self.assertIn("ἐν τῷ ὀνόματι", wh)

    def text(self, wit, ref):
        return self.q("select text from verses where corpus='grnt' and witness=? and ref=?", wit, ref)["text"]

    def test_displacement_1tim_1_1_tr_byz_printed_order(self):
        tr = self.text("TR", "1Tim.1.1")
        self.assertIn("ἀπόστολος Ἰησοῦ Χριστοῦ κατ᾽", tr)
        self.assertIn("καὶ κυριόυ Ἰησοῦ Χριστοῦ τῆς", tr)  # κυριόυ: upstream TAGNT spelling (errata)
        self.assertNotIn("Χριστοῦ Ἰησοῦ", tr)
        byz = self.text("Byz", "1Tim.1.1")
        self.assertIn("Ἰησοῦ Χριστοῦ κατ᾽", byz)
        self.assertIn("καὶ Ἰησοῦ Χριστοῦ τῆς", byz)
        self.assertNotIn("Χριστοῦ Ἰησοῦ", byz)
        self.assertIn("ἀπόστολος Χριστοῦ Ἰησοῦ κατ᾽", self.text("SBL", "1Tim.1.1"))  # NA/SBL order unchanged

    def test_displacement_acts_20_28_tr_byz(self):
        self.assertTrue(self.text("TR", "Acts.20.28").endswith("διὰ τοῦ ἰδίου αἵματος."))
        self.assertTrue(self.text("Byz", "Acts.20.28").endswith("διὰ τοῦ ἰδίου αἵματος."))
        self.assertTrue(self.text("SBL", "Acts.20.28").endswith("διὰ τοῦ αἵματος τοῦ ἰδίου."))

    def test_displacement_backward_and_swap(self):
        self.assertIn("ὑμεῖς δὲ βαπτισθήσεσθε ἐν πνεύματι ἁγίῳ", self.text("TR", "Acts.1.5"))
        self.assertIn("ὑμεῖς δὲ ἐν πνεύματι βαπτισθήσεσθε ἁγίῳ", self.text("SBL", "Acts.1.5"))
        tr = self.text("TR", "Acts.1.13")
        self.assertIn("εἰσῆλθον, ἀνέβησαν εἰς τὸ ὑπερῷον", tr)
        self.assertIn("Πέτρος καὶ Ἰάκωβος καὶ Ἰωάννης καὶ Ἀνδρέας", tr)

    def test_displacement_to_other_verse_stays_in_place(self):
        self.assertTrue(self.text("Byz", "Rom.16.25").startswith("Τῷ δὲ δυναμένῳ"))

    def test_variants_rows(self):
        self.assertIsNotNone(self.q("select 1 from variants where ref='Acts.8.37'"))
        r = self.q("select * from variants where ref='Acts.2.38' and reading='ἔφη'")
        self.assertIn("TR", r["editions"])

    def test_words_have_editions_and_strongs(self):
        w = self.q("select * from words where corpus='grnt' and ref='John.1.1' and pos=5")
        self.assertIn("SBL", w["editions"])
        self.assertEqual(w["strongs"], "G3056")
        self.assertEqual(w["lemma"], "λόγος")

    def test_fixture_hebrew_strongs_join_lexicon(self):
        n = self.q("select count(*) c from words w where corpus='hebot' and strongs!='' and not exists "
                   "(select 1 from lexicon l where l.strongs=w.strongs)")["c"]
        self.assertEqual(n, 0)

    def test_lexicon_has_ekklesia(self):
        self.assertIsNotNone(self.q("select 1 from lexicon where lemma='ἐκκλησία'"))
        self.assertIsNotNone(self.q("select 1 from lexicon where lang='heb'"))

    def test_meta(self):
        self.assertIsNotNone(self.q("select 1 from meta where key='built_at'"))
        self.assertIsNotNone(self.q("select 1 from meta where key='manifest_sha256'"))

    def test_osis_refs_only(self):
        for r in self.conn.execute("select distinct ref from words"):
            self.assertRegex(r["ref"], r"^[1-3]?[A-Za-z]+\.\d+\.\d+$")


class SyntheticEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.src = Path(self.tmp) / "sources"
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in ("TBESH", "TBESG"):  # lexicons are required inputs; empty ones are enough here
            write_xz(self.src / "stepbible" / f"{name}.txt.xz", "preamble\n")

    def tahot(self, rows):
        write_xz(self.src / "stepbible" / "TAHOT_Gen-Deu.txt.xz",
                 "preamble\n\n# Gen.4.8\tx\n" + TAHOT_HDR + "\n" + "\n".join(rows) + "\n")

    def test_x_and_r_excluded_from_wlc_but_kept_in_words(self):
        self.tahot([tahot_row("Gen.4.8#01=L", "אָב"),
                    tahot_row("Gen.4.8#0501=X", "נֵלְכָה"),
                    tahot_row("Gen.4.8#0502=R", "הַ/שָּׂדֶה"),
                    tahot_row("Gen.4.8#02=L", "אִם\\־"),
                    tahot_row("Gen.4.8#03=L", "תִּשְׁמַע\\׃")])
        conn = build(self.src, Path(self.tmp) / "t.db")
        text = conn.execute("select text from verses where witness='WLC'").fetchone()["text"]
        self.assertEqual(text, "אב אם־תשמע׃".replace("אב", "אָב").replace("אם", "אִם").replace("תשמע", "תִּשְׁמַע"))
        self.assertNotIn("נֵלְכָה", text)
        rows = conn.execute("select editions, surface from words order by pos").fetchall()
        self.assertEqual(len(rows), 5)
        self.assertEqual([r["editions"] for r in rows], ["L", "X", "R", "L", "L"])
        self.assertEqual(rows[2]["surface"], "הַשָּׂדֶה")

    def test_paragraph_markers_dropped(self):
        self.tahot([tahot_row("Gen.4.8#01=L", "אָב"),
                    tahot_row("Gen.4.8#02=L", "אִם\\׃\\ \\ס")])
        conn = build(self.src, Path(self.tmp) / "t.db")
        t = conn.execute("select text, match_key from verses where witness='WLC'").fetchone()
        self.assertTrue(t["text"].endswith("׃"))
        self.assertFalse(t["match_key"].endswith(" ס"))
        for r in conn.execute("select surface from words"):
            self.assertNotIn(" ", r["surface"])

    def test_hebrew_strongs_joins_lexicon_without_instance_suffix(self):
        self.tahot([tahot_row("Gen.4.8#01=L", "אָב", root="H0001A_B")])
        conn = build(self.src, Path(self.tmp) / "t.db")
        self.assertEqual(conn.execute("select strongs from words").fetchone()[0], "H0001A")

    def test_greek_compound_displacement_tokens(self):
        hdr = ("Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\tDictionary form =  Gloss\t"
               "editions\tMeaning variants\tSpelling variants\tSpanish translation\tSub-meaning\tConjoin word\t"
               "sStrong+Instance\tAlt Strongs")
        rows = ["\t".join(["Rom.16.25#01=K", "Τῷ (Tō)", "to", "G3588=T-DSM", "ὁ=the", ed, "", "", "", "", "#01", "G3588", "", "", "", "", ""])
                for ed in ("Byz«14.24",)]
        rows.append("\t".join(["Rom.16.25#02=K", "δὲ (de)", "now", "G1161=CONJ", "δέ=but", "Tyn»1»1+TR", "", "", "", "", "#02", "G1161", "", "", "", "", ""]))
        write_xz(self.src / "stepbible" / "TAGNT_Act-Rev.txt.xz", "\ufeffpre\n\n" + hdr + "\n" + "\n".join(rows) + "\n")
        conn = build(self.src, Path(self.tmp) / "t.db")
        self.assertEqual(conn.execute("select text from verses where witness='Byz'").fetchone()[0], "Τῷ")
        self.assertEqual(conn.execute("select text from verses where witness='THGNT'").fetchone()[0], "δὲ")

    def test_ketiv_unparseable_is_skipped(self):
        self.tahot([tahot_row("Gen.4.8#01=Q(K)", "אָב", kmean="B= weird (x) ¦ K= y", kspell="L= x"),
                    tahot_row("Gen.4.8#02=L", "אִם")])
        conn = build(self.src, Path(self.tmp) / "t.db")
        self.assertIsNone(conn.execute("select 1 from verses where witness='Ketiv'").fetchone())

    def test_ketiv_from_spelling_column(self):
        self.tahot([tahot_row("Gen.4.8#01=Q(k)", "הַיְצֵ֣א", kspell="L= הַוְצֵ֣א ¦ ;K= הוֹצֵא"),
                    tahot_row("Gen.4.8#02=L", "אִם")])
        conn = build(self.src, Path(self.tmp) / "t.db")
        k = conn.execute("select text from verses where witness='Ketiv'").fetchone()["text"]
        self.assertEqual(k, "הוֹצֵא אִם")

    def test_greek_kjv_alt_ref_wins(self):
        hdr = ("Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\tDictionary form =  Gloss\t"
               "editions\tMeaning variants\tSpelling variants\tSpanish translation\tSub-meaning\tConjoin word\t"
               "sStrong+Instance\tAlt Strongs")
        eds = "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz"
        row = "\t".join(["Act.2.11[2.10]#01=NKO", "Κρῆτες, (Krētes)", "Cretans", "G2912=N-NPM", "Κρής=Cretan",
                          eds, "", "", "", "", "#01", "G2912", "", "", "", "", ""])
        write_xz(self.src / "stepbible" / "TAGNT_Act-Rev.txt.xz", "﻿pre\n\n" + hdr + "\n" + row + "\n")
        conn = build(self.src, Path(self.tmp) / "t.db")
        self.assertIsNotNone(conn.execute("select 1 from verses where corpus='grnt' and ref='Acts.2.10'").fetchone())
        self.assertIsNone(conn.execute("select 1 from verses where corpus='grnt' and ref='Acts.2.11'").fetchone())


class MissingDb(unittest.TestCase):
    def test_db_path_env(self):
        old = os.environ.get("OTS_DB")
        os.environ["OTS_DB"] = "/nonexistent/x.db"
        try:
            self.assertEqual(str(db.db_path()), "/nonexistent/x.db")
            with self.assertRaises(SystemExit) as cm:
                db.require_db()
            self.assertEqual(cm.exception.code, 2)
        finally:
            if old is None:
                del os.environ["OTS_DB"]
            else:
                os.environ["OTS_DB"] = old

    @unittest.skipUnless((ROOT / "scripts" / "lookup.py").exists(), "lookup.py arrives in Task 9")
    def test_missing_db_exit_2(self):
        r = subprocess.run([sys.executable, "scripts/lookup.py", "verse", "John.1.1"], cwd=ROOT,
                           env={**os.environ, "OTS_DB": "/nonexistent.db"}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("bible.db not found", r.stderr)


if __name__ == "__main__":
    unittest.main()
