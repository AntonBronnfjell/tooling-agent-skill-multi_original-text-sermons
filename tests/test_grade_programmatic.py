import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRADER = ROOT / "evals" / "grade_programmatic.py"
EVALS = ROOT / "evals" / "evals.json"


class GradeProgrammaticTest(unittest.TestCase):
    def test_fake_run_dir(self):
        with tempfile.TemporaryDirectory() as d:
            run = Path(d)
            (run / "sermons").mkdir()
            (run / "sermons" / "x.en.md").write_text("no frontmatter, ἐκκλησία here\n", encoding="utf-8")
            (run / "transcript.md").write_text("ran lookup.py usage ἐκκλησία\n", encoding="utf-8")
            p = subprocess.run([sys.executable, str(GRADER), str(run), "--expect", "ἐκκλησία",
                                "--expect", "אור", "--forbid", "church"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["sermon_files"], ["x.en.md"])
            self.assertTrue(out["has_transcript"])
            r = out["check_sermon"][0]
            self.assertEqual(r["file"], "x.en.md")
            self.assertIn(r["exit"], (1, 2))  # invalid sermon (1) or db missing (2)
            self.assertTrue(r["errors"])
            self.assertEqual(out["expect"]["ἐκκλησία"], {"sermons": True, "transcript": True})
            self.assertEqual(out["expect"]["אור"], {"sermons": False, "transcript": False})
            self.assertEqual(out["forbid"]["church"], {"sermons": False, "transcript": False})

    def test_empty_run_dir(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run([sys.executable, str(GRADER), d], capture_output=True, text=True)
            out = json.loads(p.stdout)
            self.assertEqual(out["check_sermon"], [])
            self.assertFalse(out["has_transcript"])


class EvalsJsonTest(unittest.TestCase):
    def test_shape(self):
        data = json.loads(EVALS.read_text(encoding="utf-8"))
        self.assertEqual(data["skill_name"], "original-text-sermons")
        evs = data["evals"]
        self.assertEqual([e["id"] for e in evs], list(range(1, 13)))
        names = [e["name"] for e in evs]
        self.assertEqual(len(set(names)), 12)
        for e in evs:
            for k in ("prompt", "expected_output", "files", "assertions"):
                self.assertIn(k, e)
            self.assertEqual(e["files"], [])
            self.assertTrue(e["assertions"] and all(isinstance(a, str) and a for a in e["assertions"]))


if __name__ == "__main__":
    unittest.main()
