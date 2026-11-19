import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "check-sermon-hook.sh"
INSTALL = ROOT / "install.sh"
NEG = ROOT / "evals" / "fixtures" / "negative"
POS = ROOT / "evals" / "fixtures" / "positive"
HAVE_DB = (ROOT / "data" / "bible.db").is_file()


def hook(payload, raw=None, env=None):
    e = dict(os.environ)
    e.update(env or {})
    data = raw if raw is not None else json.dumps(payload)
    return subprocess.run(["bash", str(HOOK)], input=data, capture_output=True, text=True, env=e)


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sermons = Path(self.tmp.name) / "sermons"
        self.sermons.mkdir()

    def put(self, src):
        dst = self.sermons / src.name
        shutil.copy(src, dst)
        return dst

    @unittest.skipUnless(HAVE_DB, "data/bible.db not built")
    def test_hook_blocks_bad_sermon(self):
        p = self.put(NEG / "misquote.md")
        r = hook({"tool_input": {"file_path": str(p)}})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("not found", r.stderr)

    @unittest.skipUnless(HAVE_DB, "data/bible.db not built")
    def test_hook_passes_good_sermon(self):
        p = self.put(POS / "john-1-1-with-note.md")
        self.assertEqual(hook({"tool_input": {"file_path": str(p)}}).returncode, 0)

    @unittest.skipUnless(HAVE_DB, "data/bible.db not built")
    def test_hook_cursor_shape_checks_sermon(self):
        p = self.put(NEG / "misquote.md")
        self.assertEqual(hook({"file_path": str(p)}).returncode, 2)

    def test_hook_missing_db_does_not_block(self):
        p = self.put(NEG / "misquote.md")
        r = hook({"tool_input": {"file_path": str(p)}}, env={"OTS_DB": str(Path(self.tmp.name) / "none.db")})
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stderr.strip())

    def test_hook_ignores_other_files(self):
        r = hook({"tool_input": {"file_path": "/tmp/x.py"}})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_hook_ignores_non_sermon_md(self):
        r = hook({"tool_input": {"file_path": "/tmp/notes/x.md"}})
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_hook_cursor_shape(self):
        self.assertEqual(hook({"file_path": "/tmp/x.py"}).returncode, 0)

    def test_hook_malformed_json_silent(self):
        r = hook(None, raw="not json {")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        r = hook(None, raw="")
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    @unittest.skipUnless(HAVE_DB, "data/bible.db not built")
    def test_hook_follows_symlink(self):
        link = Path(self.tmp.name) / "linkedhooks"
        link.symlink_to(ROOT)
        p = self.put(NEG / "misquote.md")
        r = subprocess.run(["bash", str(link / "hooks" / "check-sermon-hook.sh")],
                           input=json.dumps({"file_path": str(p)}), capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stderr)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        for d in (".claude/skills", ".cursor/skills", ".agents/skills"):
            (self.home / d).mkdir(parents=True)
        # .copilot deliberately absent
        self.db = Path(self.tmp.name) / "bible.db"
        self.db.write_text("x")
        self.env = {**os.environ, "HOME": str(self.home), "OTS_DB": str(self.db), "OTS_NO_GIT": "1"}

    def run_install(self, *args):
        return subprocess.run(["bash", str(INSTALL), *args], capture_output=True, text=True,
                              env=self.env, cwd=self.tmp.name)

    def snapshot(self):
        out = {}
        for p in sorted(self.home.rglob("*")):
            if p.is_symlink():
                out[str(p)] = os.readlink(p)
            elif p.is_file():
                out[str(p)] = p.read_text()
        return out

    def test_install_links_only_existing_dirs(self):
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for d in (".claude", ".cursor", ".agents"):
            link = self.home / d / "skills" / "original-text-sermons"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.resolve(), ROOT.resolve())
        self.assertFalse((self.home / ".copilot").exists())

    def test_install_twice_changes_nothing(self):
        self.assertEqual(self.run_install().returncode, 0)
        first = self.snapshot()
        r = self.run_install()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.snapshot(), first)

    def test_cursor_hook_wired_and_claude_settings_untouched(self):
        self.run_install()
        cfg = json.loads((self.home / ".cursor" / "hooks.json").read_text())
        cmds = [h["command"] for h in cfg["hooks"]["afterFileEdit"]]
        self.assertEqual(len(cmds), 1)
        self.assertTrue(cmds[0].endswith("hooks/check-sermon-hook.sh"))
        self.assertFalse((self.home / ".claude" / "settings.json").exists())

    def test_existing_cursor_hooks_preserved_and_backed_up(self):
        path = self.home / ".cursor" / "hooks.json"
        orig = {"version": 1, "hooks": {"afterFileEdit": [{"command": "other.sh"}],
                                        "stop": [{"command": "s.sh"}]}}
        path.write_text(json.dumps(orig))
        self.run_install()
        cfg = json.loads(path.read_text())
        self.assertEqual(cfg["hooks"]["stop"], [{"command": "s.sh"}])
        self.assertEqual(cfg["hooks"]["afterFileEdit"][0], {"command": "other.sh"})
        self.assertEqual(len(cfg["hooks"]["afterFileEdit"]), 2)
        self.assertEqual(json.loads((self.home / ".cursor" / "hooks.json.bak").read_text()), orig)

    def test_uninstall_removes_only_ours(self):
        path = self.home / ".cursor" / "hooks.json"
        path.write_text(json.dumps({"version": 1, "hooks": {"afterFileEdit": [{"command": "other.sh"}]}}))
        foreign = self.home / ".agents" / "skills" / "other"
        foreign.symlink_to("/tmp")
        # symlink to something else under our name must survive
        (self.home / ".cursor" / "skills" / "original-text-sermons").symlink_to("/tmp")
        self.run_install()
        self.assertEqual(os.readlink(self.home / ".cursor/skills/original-text-sermons"), "/tmp")
        r = self.run_install("--uninstall")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.home / ".claude/skills/original-text-sermons").exists())
        self.assertFalse((self.home / ".claude/skills/original-text-sermons").is_symlink())
        self.assertFalse((self.home / ".agents/skills/original-text-sermons").is_symlink())
        self.assertTrue(foreign.is_symlink())
        self.assertEqual(os.readlink(self.home / ".cursor/skills/original-text-sermons"), "/tmp")
        cfg = json.loads(path.read_text())
        self.assertEqual(cfg["hooks"]["afterFileEdit"], [{"command": "other.sh"}])
        self.assertTrue((self.home / ".cursor" / "hooks.json.bak").exists())

    def test_non_symlink_path_refused(self):
        target = self.home / ".claude" / "skills" / "original-text-sermons"
        target.mkdir()
        (target / "keep.txt").write_text("mine")
        r = self.run_install()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refus", (r.stdout + r.stderr).lower())
        self.assertEqual((target / "keep.txt").read_text(), "mine")
        self.assertFalse(target.is_symlink())

    def test_status(self):
        self.run_install()
        r = self.run_install("--status")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(str(self.home / ".claude/skills/original-text-sermons"), r.stdout)
        self.assertIn("cursor", r.stdout.lower())
        self.assertIn("frontmatter", r.stdout.lower())

    def test_skill_frontmatter_declares_hook(self):
        head = (ROOT / "SKILL.md").read_text().split("---")[1]
        self.assertIn("PostToolUse", head)
        self.assertIn("check-sermon-hook.sh", head)

    def test_snippets_are_valid_json(self):
        for n in ("claude-code.json", "cursor-hooks.json"):
            json.loads((ROOT / "hooks" / n).read_text())


if __name__ == "__main__":
    unittest.main()
