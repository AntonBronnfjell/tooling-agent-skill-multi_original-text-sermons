# Hooks

`check-sermon-hook.sh` runs `scripts/check_sermon.py` on a sermon right after the agent writes it.

## Behaviour

- Reads hook JSON on stdin: Claude Code `tool_input.file_path`, Cursor `file_path`.
- Only paths matching `*/sermons/*.md` are checked; anything else, or malformed JSON, exits 0 silently.
- Validator errors (exit 1): output goes to stderr and the hook exits 2, which Claude Code feeds back to the model so it fixes the sermon.
- Database missing or invalid (validator exit 2): a message goes to stderr and the hook exits 0. Writes are never blocked just because `data/bible.db` has not been built; run `./install.sh`.
- Warnings alone never fail.
- The repo is located from the script's own real path (symlinks followed), so the installed symlink works.

## Wiring

- **Claude Code (2.1.311 checked):** `SKILL.md` frontmatter supports `hooks:` (docs: code.claude.com/docs/en/skills, `hooks` field; /hooks#hooks-in-skills-and-agents). The skill declares a `PostToolUse` hook on `Write|Edit`, registered when the skill is invoked and kept for the rest of the session. `install.sh` therefore does NOT touch `~/.claude/settings.json`. The command uses `$HOME/.claude/skills/original-text-sermons/...`, which `install.sh` creates. Caveats: not active before the skill is invoked; a locked-down org (`strictPluginOnlyCustomization`) may disable frontmatter hooks. `claude-code.json` is the equivalent settings.json snippet to merge manually in that case.
- **Cursor:** `install.sh` adds an `afterFileEdit` entry (see `cursor-hooks.json`, `__REPO__` replaced by the repo path) to `~/.cursor/hooks.json` if `~/.cursor` exists. Idempotent; the original is saved once to `hooks.json.bak`; other entries are preserved. `--uninstall` removes only that entry.
- **Copilot:** no hook; SKILL.md covers validation as a workflow step.
- **Repo dev:** `pre-commit` (enabled via `git config core.hooksPath hooks`) runs the unit tests, `lint_skill.py`, and `check_sermon.py` on `evals/fixtures/positive/*.md` (skipped with a message when the DB is missing).
