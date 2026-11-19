"""Uncertain word order is flagged in the DB and surfaced by lookup and check_sermon."""
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import build_db  # noqa: E402
import test_lookup  # noqa: E402
from check_sermon import check  # noqa: E402
from otslib import db  # noqa: E402
from test_build_stepbible import FIXTURES, build, write_xz  # noqa: E402
from test_check_sermon import EN, body, fm  # noqa: E402

HDR = ("Word & Type\tGreek\tEnglish translation\tdStrongs = Grammar\tDictionary form =  Gloss\t"
       "editions\tMeaning variants\tSpelling variants\tSpanish translation\tSub-meaning\tConjoin word\t"
       "sStrong+Instance\tAlt Strongs")
ALL = "NA28+NA27+Tyn+SBL+WH+Treg+TR+Byz"


def row(ref, n, greek, eds):
    return "\t".join([f"{ref}#{n:02d}=NKO", f"{greek} (x)", "g", "G0001=N", "λ=g", eds, "", "", "", "", f"#{n:02d}",
                      "G0001", "", "", "", "", ""])


class StepbibleFlags(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = Path(self.tmp) / "src"
        shutil.copytree(FIXTURES, self.src)

    def flags(self, rows):
        write_xz(self.src / "stepbible" / "TAGNT_Act-Rev.txt.xz",
                 "﻿pre\n\n" + HDR + "\n" + "\n".join(rows) + "\n")
        conn = build(self.src, Path(self.tmp) / "t.db", only=("stepbible",), case=self)
        return {(r["witness"], r["ref"], r["reason"]) for r in conn.execute("SELECT * FROM order_flags WHERE ref='Rom.1.1'")}

    def test_moved_word_over_partial_word_is_flagged(self):
        f = self.flags([row("Rom.1.1", 1, "α", ALL.replace("Tyn", "Tyn»2")),
                        row("Rom.1.1", 2, "β", "NA28+Tyn+SBL"),  # not printed by every edition
                        row("Rom.1.1", 3, "γ", ALL)])
        self.assertEqual(f, {("THGNT", "Rom.1.1", "order uncertain")})

    def test_moved_word_over_universal_words_is_not_flagged(self):
        f = self.flags([row("Rom.1.1", 1, "α", ALL.replace("Tyn", "Tyn»2")),
                        row("Rom.1.1", 2, "β", ALL), row("Rom.1.1", 3, "γ", ALL)])
        self.assertEqual(f, set())

    def test_diapantos_verse_with_a_move_is_flagged(self):
        f = self.flags([row("Rom.1.1", 1, "α", ALL.replace("WH", "WH»1")),
                        row("Rom.1.1", 2, "διὰ παντὸς", ALL), row("Rom.1.1", 3, "γ", ALL)])
        self.assertEqual(f, {("WH", "Rom.1.1", "order uncertain")})

    def test_sbl_is_never_flagged(self):  # SBL verse text is MACULA's, not a TAGNT reordering
        f = self.flags([row("Rom.1.1", 1, "α", ALL.replace("SBL", "SBL»2")),
                        row("Rom.1.1", 2, "β", "NA28+Tyn+SBL"), row("Rom.1.1", 3, "γ", ALL)])
        self.assertEqual(f, set())

    def test_unmoved_verse_is_not_flagged_even_with_partial_words(self):
        f = self.flags([row("Rom.1.1", 1, "α", ALL), row("Rom.1.1", 2, "β", "NA28+Tyn+SBL")])
        self.assertEqual(f, set())


class Surfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.dbfile = os.path.join(cls.tmp, "t.db")
        build_db.build(Path(FIXTURES), Path(cls.dbfile), out=io.StringIO())
        c = sqlite3.connect(cls.dbfile)
        c.executemany("INSERT INTO order_flags VALUES ('grnt',?,?,?)", [
            ("THGNT", "John.1.1", "order uncertain"),
            ("TR", "1Tim.1.1", "known scrambled"),
            ("TR", "Acts.20.28", "verse break follows KJV")])
        c.commit()
        c.close()
        test_lookup.Lookup.db = cls.dbfile
        cls.conn = db.connect(cls.dbfile)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp)

    def verse(self, ref, wit):
        return test_lookup.run("verse", ref, "--witness", wit)

    def test_lookup_flags_uncertain_order(self):
        v = self.verse("John.1.1", "THGNT")
        self.assertIs(v["order_uncertain"], True)
        self.assertIn("printed edition", v["order_note"])

    def test_lookup_known_scrambled_is_uncertain(self):
        self.assertIs(self.verse("1Tim.1.1", "TR")["order_uncertain"], True)

    def test_lookup_kjv_break_is_informational_only(self):
        v = self.verse("Acts.20.28", "TR")
        self.assertNotIn("order_uncertain", v)
        self.assertIn("KJV", v["order_note"])

    def test_lookup_unflagged_has_no_field(self):
        v = self.verse("John.1.1", "SBL")
        self.assertNotIn("order_uncertain", v)

    def test_order_note_no_longer_claims_tagnt_rebuild_for_tr(self):
        self.assertNotIn("rebuilt from TAGNT", self.verse("Acts.20.28", "TR").get("order_note", ""))

    def run_text(self, quote):
        p = Path(self.tmp) / "s.md"
        p.write_text(fm(passage="John.1.1") + body(quote=quote), encoding="utf-8")
        return check(p, self.conn)

    def test_check_warns_on_uncertain_order(self):
        q = "> [GRC:THGNT John.1.1] ἐν ἀρχῇ ἦν ὁ λόγος\n> Literal: in beginning was the word\n> Natural: in the beginning was the word\n"
        got = [f for f in self.run_text(q) if "order uncertain" in f.msg]
        self.assertEqual([f.level for f in got], ["WARN"])
        self.assertIn("order uncertain for THGNT John.1.1: verify against a printed edition", got[0].msg)

    def test_check_errors_on_known_scrambled_tr(self):
        q = ("> [GRC:TR 1Tim.1.1] Παῦλος ἀπόστολος\n> Literal: Paul apostle\n> Natural: Paul, an apostle\n")
        got = [f for f in self.run_text(q) if "known to be wrong" in f.msg]
        self.assertEqual([f.level for f in got], ["ERROR"])
        self.assertIn("TR word order for 1Tim.1.1 is known to be wrong in the data; quote another witness", got[0].msg)

    def test_check_silent_for_kjv_break_and_unflagged(self):
        q = "> [GRC:TR Acts.20.28] καὶ\n> Literal: and\n> Natural: and\n"
        self.assertFalse([f for f in self.run_text(q) if "order" in f.msg])
        q = "> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος\n> Literal: and god was the word\n> Natural: and the word was God\n"
        self.assertFalse([f for f in self.run_text(q) if "order" in f.msg])


class MetaSummary(unittest.TestCase):
    def test_summary_equals_final_order_flags(self):
        with tempfile.TemporaryDirectory() as d:
            conn = build(FIXTURES, os.path.join(d, "t.db"), only=("stepbible", "versification", "macula", "greek_editions"))
            meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
            want = "; ".join(f"{w}: {r}={n}" for w, r, n in conn.execute(
                "SELECT witness, reason, count(*) FROM order_flags GROUP BY 1, 2 ORDER BY 1, 2"))
            conn.close()
        self.assertEqual(meta["order_flags_summary"], want)
        self.assertNotIn("tagnt_order_uncertain_verses", meta)


class GreekEditionFlags(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = Path(self.tmp) / "src"
        shutil.copytree(FIXTURES, self.src)

    def build(self, tagnt, byz):
        write_xz(self.src / "stepbible" / "TAGNT_Act-Rev.txt.xz",
                 "\ufeffpre\n\n" + HDR + "\n" + "\n".join(tagnt) + "\n")
        write_xz(self.src / "byz" / "ROM.csv.xz", "chapter,verse,text\n" + byz)
        return build(self.src, Path(self.tmp) / "t.db", only=("stepbible", "versification", "macula", "greek_editions"),
                     case=self)

    def reasons(self, conn, wit):
        out = {}
        for r in conn.execute("SELECT ref, reason FROM order_flags WHERE witness=?", (wit,)):
            out.setdefault(r["ref"], set()).add(r["reason"])
        return out

    def test_words_moved_across_a_verse_break_are_flagged_on_both_verses(self):
        w = "αλφα βητα γαμμα δελτα εψιλον ζητα ηττα θητα ιωτα καππα λαμβδα μυ".split()
        tagnt = [row("Rom.1.9", i + 1, x, ALL) for i, x in enumerate(w[:6])] + \
                [row("Rom.1.10", i + 1, x, ALL) for i, x in enumerate(w[6:])]
        conn = self.build(tagnt, f'1,9,"{" ".join(w[:8])}"\n1,10,"{" ".join(w[8:])}"\n')
        r = self.reasons(conn, "Byz")
        self.assertEqual(r.get("Rom.1.9"), {"verse break follows KJV"})
        self.assertEqual(r.get("Rom.1.10"), {"verse break follows KJV"})

    def test_renumbered_whole_verses_are_not_boundary_moves(self):  # Byz prints Rom 16:25-27 after 14:23
        c = build(FIXTURES, os.path.join(self.tmp, "t.db"),
                  only=("stepbible", "versification", "macula", "greek_editions"), case=self)
        self.assertNotIn("verse break follows KJV", self.reasons(c, "Byz").get("Rom.16.25", set()))

    def test_known_scrambled_tr_verses_are_marked(self):
        w = "αλφα βητα".split()
        tagnt = [row("1Ti.1.2", i + 1, x, ALL) for i, x in enumerate(w)]
        conn = self.build(tagnt, "")
        self.assertEqual(self.reasons(conn, "TR").get("1Tim.1.2"), {"known scrambled"})


if __name__ == "__main__":
    unittest.main()
