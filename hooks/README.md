# Hooks

`check-sermon-hook.sh` runs `scripts/check_sermon.py` on a sermon right after the agent writes it.

## Behaviour

- Reads hook JSON on stdin: Claude Code `tool_input.file_path`, Cursor `file_path`.
- Only paths matching `*/sermons/*.md` are checked; anything else, or malformed JSON, exits 0 silently.
- Validator errors (exit 1): output goes to stderr and the hook exits 2, which Claude Code feeds back to the model so it fixes the sermon.
- Database missing or invalid (validator exit 2): a message goes to stderr and the hook exits 0. Writes are never blocked just because `data/bible.db` has not been built; run `./install.sh`.
- Warnings alone never fail. With a Claude Code payload (`tool_input`), warnings are returned on stdout as `{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"…"}}` with exit 0, which Claude Code adds next to the tool result (checked against code.claude.com/docs/en/hooks: stdout JSON is read on exit 0 only; exit-2 stderr is shown to the model). With a Cursor payload, warnings go to stderr.
- A clean pass is silent: the validator's `OK <file>` line is dropped.
- **Cursor caveat:** `afterFileEdit` output (stdout, stderr, exit code) may never reach the agent. In Cursor the hook is a convenience; the enforcement is SKILL.md step 10 (run `check_sermon.py` and fix every ERROR before presenting the sermon).
- The repo is located from the script's own real path (symlinks followed), so the installed symlink works.

## Wiring

- **Claude Code (2.1.311 checked):** `SKILL.md` frontmatter supports `hooks:` (docs: code.claude.com/docs/en/skills, `hooks` field; /hooks#hooks-in-skills-and-agents). The skill declares a `PostToolUse` hook on `Write|Edit`, registered when the skill is invoked and kept for the rest of the session. `install.sh` therefore does NOT touch `~/.claude/settings.json`. The command is a POSIX `sh` fallback chain that execs the first existing `hooks/check-sermon-hook.sh` under `$CLAUDE_PROJECT_DIR/.claude/skills`, `~/.claude/skills`, `~/.agents/skills`, `~/.copilot/skills`, `~/.cursor/skills` (each `/original-text-sermons`), passing stdin through; if none exists it prints `original-text-sermons: validator hook not found — run install.sh` to stderr and exits 0. `install.sh` warns when `~/.claude/skills` is missing. Caveats: not active before the skill is invoked; a locked-down org (`strictPluginOnlyCustomization`) may disable frontmatter hooks. `claude-code.json` is the equivalent settings.json snippet to merge manually in that case.
- **Cursor:** `install.sh` adds an `afterFileEdit` entry (see `cursor-hooks.json`, `__REPO__` replaced by the repo path) to `~/.cursor/hooks.json` if `~/.cursor` exists. The command is written as a quoted shell string so paths with spaces work. Invalid JSON in `hooks.json` makes install/uninstall print `Cursor hook NOT wired ... not valid JSON` and exit non-zero without touching the file. Idempotent; the original is saved once to `hooks.json.bak`; other entries are preserved. `--uninstall` removes only that entry.
- **Copilot:** no hook; SKILL.md covers validation as a workflow step.
- **Repo dev:** `pre-commit` (enabled via `git config core.hooksPath hooks`) runs the unit tests, `lint_skill.py`, and `check_sermon.py` on `evals/fixtures/positive/*.md` (skipped with a message when the DB is missing).

## Environment

- `OTS_DB`: database path (default `data/bible.db`).
- `OTS_NO_GIT=1`: `install.sh` skips setting/unsetting the repo-local `core.hooksPath` (used by tests).
