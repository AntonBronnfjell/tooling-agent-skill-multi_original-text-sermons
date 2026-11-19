import io
import sqlite3
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_sblgnt as cs  # noqa: E402

SOURCES = ROOT / "tests" / "fixtures" / "sources"

# what MACULA-derived SBL rows look like for the fixture range (apparatus marks and brackets gone)
DB = {
    "Rom.16.20": "ὁ δὲ θεὸς τῆς εἰρήνης συντρίψει τὸν Σατανᾶν ὑπὸ τοὺς πόδας ὑμῶν ἐν τάχει. "
                 "ἡ χάρις τοῦ κυρίου ἡμῶν Ἰησοῦ Χριστοῦ μεθ’ ὑμῶν.",
    "Rom.16.21": "Ἀσπάζεται ὑμᾶς Τιμόθεος ὁ συνεργός μου, καὶ Λούκιος καὶ Ἰάσων καὶ Σωσίπατρος οἱ συγγενεῖς μου.",
    "Rom.16.22": "ἀσπάζομαι ὑμᾶς ἐγὼ Τέρτιος ὁ γράψας τὴν ἐπιστολὴν ἐν κυρίῳ.",
    "Rom.16.23": "ἀσπάζεται ὑμᾶς Γάϊος ὁ ξένος μου καὶ ὅλης τῆς ἐκκλησίας. "
                 "ἀσπάζεται ὑμᾶς Ἔραστος ὁ οἰκονόμος τῆς πόλεως καὶ Κούαρτος ὁ ἀδελφός.",
    "Rom.16.24": "Ἡ χάρις τοῦ κυρίου ἡμῶν Ἰησοῦ Χριστοῦ μετὰ πάντων ὑμῶν. Ἀμήν.",
}


_OPEN = []


def make_db(rows):
    c = sqlite3.connect(":memory:")
    _OPEN.append(c)
    c.execute("CREATE TABLE verses (corpus TEXT, witness TEXT, ref TEXT, text TEXT, match_key TEXT)")
    c.executemany("INSERT INTO verses VALUES ('grnt','SBL',?,?,'')", rows.items())
    return c


class CheckSblgnt(unittest.TestCase):
    def tearDown(self):
        while _OPEN:
            _OPEN.pop().close()

    def test_parse_strips_apparatus_marks(self):
        fl = cs.load_faithlife(SOURCES / "sblgnt")
        self.assertIn(("Rom", 16, 24), fl)
        self.assertNotIn("⸀", fl[("Rom", 16, 21)])
        self.assertNotIn("⸂", fl[("Rom", 16, 24)])

    def test_rom_16_25_27_absent_in_faithlife_file(self):
        fl = cs.load_faithlife(SOURCES / "sblgnt")
        self.assertEqual([v for v in (25, 26, 27) if ("Rom", 16, v) in fl], [])
        self.assertIn(("Rom", 16, 24), fl)  # the file does print 16:24

    def test_matching_db_has_no_mismatch(self):
        rep = cs.check(make_db(DB), SOURCES / "sblgnt")
        self.assertEqual(rep["mismatches"], [])
        self.assertEqual(rep["chapters"], 1)

    def test_status_reports_file_and_db_presence(self):
        rep = cs.check(make_db(DB), SOURCES / "sblgnt")
        self.assertEqual(rep["status"]["Rom.16.25"], (False, False))
        self.assertEqual(rep["status"]["Rom.16.24"], (True, True))

    def test_punctuation_and_case_ignored(self):
        rows = dict(DB, **{"Rom.16.22": "Ἀσπάζομαι ὑμᾶς ἐγὼ Τέρτιος ὁ γράψας τὴν ἐπιστολὴν, ἐν κυρίῳ"})
        self.assertEqual(cs.check(make_db(rows), SOURCES / "sblgnt")["mismatches"], [])

    def test_word_difference_flagged(self):
        rows = dict(DB, **{"Rom.16.22": "ἀσπάζομαι ὑμᾶς ἐγὼ Τέρτιος ὁ γράψας τὴν ἐπιστολὴν ἐν Χριστῷ."})
        mm = cs.check(make_db(rows), SOURCES / "sblgnt")["mismatches"]
        self.assertEqual([m["ref"] for m in mm], ["Rom.16.22"])

    def test_extra_db_verse_flagged(self):
        rows = dict(DB, **{"Rom.16.25": "τῷ δὲ δυναμένῳ ὑμᾶς στηρίξαι"})
        rep = cs.check(make_db(rows), SOURCES / "sblgnt")
        self.assertEqual(rep["status"]["Rom.16.25"], (False, True))
        self.assertIn("Rom.16.25", [m["ref"] for m in rep["mismatches"]])

    def test_missing_db_verse_flagged(self):
        rows = {k: v for k, v in DB.items() if k != "Rom.16.23"}
        mm = cs.check(make_db(rows), SOURCES / "sblgnt")["mismatches"]
        self.assertIn("Rom.16.23", [m["ref"] for m in mm])

    def test_versification_shift_is_not_a_text_mismatch(self):
        # same words, verse boundary moved (the MACULA vs KJV situation): not a text difference
        words = DB["Rom.16.22"].split()
        rows = dict(DB, **{"Rom.16.22": " ".join(words[:4]),
                           "Rom.16.23": " ".join(words[4:]) + " " + DB["Rom.16.23"]})
        self.assertEqual(cs.check(make_db(rows), SOURCES / "sblgnt")["mismatches"], [])

    def test_known_versification_differences_are_mapped_to_kjv(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "Phil.txt").write_text(
                "Phil 1:16\tοἱ μὲν ἐξ ἀγάπης,\nPhil 1:17\tοἱ δὲ ἐξ ἐριθείας.\n", encoding="utf-8")
            (Path(t) / "Rev.txt").write_text(
                "Rev 12:17\tκαὶ ὠργίσθη ὁ δράκων.\nRev 12:18\tκαὶ ἐστάθη ἐπὶ τὴν ἄμμον.\n"
                "Rev 13:1\tΚαὶ εἶδον θηρίον.\n", encoding="utf-8")
            rows = {"Phil.1.16": "οἱ δὲ ἐξ ἐριθείας.", "Phil.1.17": "οἱ μὲν ἐξ ἀγάπης,",
                    "Rev.12.17": "καὶ ὠργίσθη ὁ δράκων.",
                    "Rev.13.1": "καὶ ἐστάθη ἐπὶ τὴν ἄμμον. Καὶ εἶδον θηρίον."}
            self.assertEqual(cs.check(make_db(rows), Path(t))["mismatches"], [])
            rows["Rev.13.1"] = "Καὶ εἶδον θηρίον."  # sentence lost from the DB
            self.assertTrue(cs.check(make_db(rows), Path(t))["mismatches"])

    def test_cli_exit_codes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            ok, bad = Path(t) / "ok.db", Path(t) / "bad.db"
            for p, rows in ((ok, DB), (bad, dict(DB, **{"Rom.16.25": "x y z"}))):
                c = sqlite3.connect(p)
                c.execute("CREATE TABLE verses (corpus TEXT, witness TEXT, ref TEXT, text TEXT, match_key TEXT)")
                c.executemany("INSERT INTO verses VALUES ('grnt','SBL',?,?,'')", rows.items())
                c.commit()
                c.close()
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cs.main(["--db", str(ok), "--sources", str(SOURCES)]), 0)
                self.assertEqual(cs.main(["--db", str(bad), "--sources", str(SOURCES)]), 1)
            self.assertIn("Rom.16.25", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
