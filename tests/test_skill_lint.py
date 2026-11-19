import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINT = ROOT / "scripts" / "lint_skill.py"

GOOD = """---
name: original-text-sermons
description: Writes sermons from the original texts. Use for sermon, sermón, prédica.
hooks: {}
---

# Skill

See [rules](references/rules.md) and [the web](https://example.org) and [top](#skill).
Run `python3 scripts/tool.py` and `scripts/build.sh`.
"""


def run_lint(root):
    return subprocess.run([sys.executable, str(LINT), str(root)], capture_output=True, text=True)


class RepoLintTests(unittest.TestCase):
    def test_lint_passes(self):
        res = subprocess.run([sys.executable, str(LINT)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_repo_docs_exist(self):
        for name in ("SKILL.md", "AGENTS.md", "README.md", "LICENSE"):
            self.assertTrue((ROOT / name).is_file(), name)


class LintRuleTests(unittest.TestCase):
    def make(self, skill=GOOD, files=("references/rules.md", "scripts/tool.py", "scripts/build.sh")):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for f in files:
            (root / f).parent.mkdir(parents=True, exist_ok=True)
            (root / f).write_text("x\n", encoding="utf-8")
        (root / "SKILL.md").write_text(skill, encoding="utf-8")
        return root

    def assertFails(self, root, needle):
        res = run_lint(root)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn(needle, res.stdout + res.stderr)

    def test_good_passes_with_extra_keys(self):
        res = run_lint(self.make())
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_missing_skill_md(self):
        root = self.make()
        os.remove(root / "SKILL.md")
        self.assertFails(root, "SKILL.md")

    def test_no_frontmatter(self):
        self.assertFails(self.make(skill="# no frontmatter\n"), "frontmatter")

    def test_wrong_name(self):
        self.assertFails(self.make(skill=GOOD.replace("name: original-text-sermons", "name: other")), "name")

    def test_missing_description(self):
        bad = "\n".join(l for l in GOOD.splitlines() if not l.startswith("description:")) + "\n"
        self.assertFails(self.make(skill=bad), "description")

    def test_description_too_long(self):
        bad = GOOD.replace("Writes sermons", "x" * 1100)
        self.assertFails(self.make(skill=bad), "1024")

    def test_unquoted_colon_in_description(self):
        # "key: a: b" is invalid YAML in a plain scalar; strict hosts would drop the skill.
        bad = GOOD.replace("Use for sermon", "Triggers: sermon")
        self.assertFails(self.make(skill=bad), "colon")

    def test_quoted_colon_in_description_ok(self):
        ok = GOOD.replace("description: Writes sermons from the original texts. Use for sermon, sermón, prédica.",
                          'description: "Triggers: sermon, sermón."')
        res = run_lint(self.make(skill=ok))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_flow_and_block_hooks_ok(self):
        ok = GOOD.replace("hooks: {}", 'hooks: {PostToolUse: [{matcher: "Write"}]}\nmeta:\n  owner: me')
        res = run_lint(self.make(skill=ok))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_too_many_lines(self):
        self.assertFails(self.make(skill=GOOD + "line\n" * 500), "500")

    def test_broken_link(self):
        self.assertFails(self.make(skill=GOOD + "[gone](references/missing.md)\n"), "references/missing.md")

    def test_link_with_anchor_resolves(self):
        res = run_lint(self.make(skill=GOOD + "[sec](references/rules.md#part)\n"))
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_missing_script(self):
        self.assertFails(self.make(skill=GOOD + "Then `scripts/gone.py`.\n"), "scripts/gone.py")

    def test_missing_shell_script(self):
        self.assertFails(self.make(skill=GOOD + "Then scripts/gone.sh.\n"), "scripts/gone.sh")


if __name__ == "__main__":
    unittest.main()
