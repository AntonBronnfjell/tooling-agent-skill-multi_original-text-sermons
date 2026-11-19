#!/usr/bin/env bash
# Install original-text-sermons into the user's agent directories.
#   ./install.sh              build data/bible.db if missing, symlink, wire hooks
#   ./install.sh --status     show symlinks and hook wiring
#   ./install.sh --uninstall  remove only what install added (backups are kept)
# Honours $HOME and $OTS_DB; OTS_NO_GIT=1 skips the repo-local core.hooksPath change (tests). Python 3 stdlib + bash only.
set -euo pipefail

NAME="original-text-sermons"
REPO="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$(dirname "${BASH_SOURCE[0]}")")"
HOOK_CMD="\"$REPO/hooks/check-sermon-hook.sh\""
DB="${OTS_DB:-$REPO/data/bible.db}"
# Antigravity (Google): global skills dir ~/.gemini/config/skills (antigravity.google/docs/skills); created when ~/.gemini exists.
ANTIGRAVITY_SKILLS="$HOME/.gemini/config/skills"
SKILL_DIRS=("$HOME/.claude/skills" "$HOME/.cursor/skills" "$HOME/.agents/skills" "$HOME/.copilot/skills" "$ANTIGRAVITY_SKILLS")
CURSOR_HOOKS="$HOME/.cursor/hooks.json"

# Cursor hooks.json editing. Modes: add | remove | status. Entry is ours iff its command == HOOK_CMD.
cursor_json() {
  python3 - "$1" "$CURSOR_HOOKS" "$HOOK_CMD" <<'PY'
import json, os, shutil, sys
mode, path, cmd = sys.argv[1:4]
try:
    cfg = json.load(open(path)) if os.path.exists(path) else {}
except ValueError:
    sys.exit("Cursor hook NOT wired: %s is not valid JSON \u2014 fix or remove it and re-run" % path)
hooks = cfg.get("hooks") if isinstance(cfg.get("hooks"), dict) else {}
entries = hooks.get("afterFileEdit") if isinstance(hooks.get("afterFileEdit"), list) else []
ours = [e for e in entries if isinstance(e, dict) and e.get("command") == cmd]
if mode == "status":
    print("wired" if ours else "not wired"); sys.exit(0)
def save(new):
    if os.path.exists(path) and not os.path.exists(path + ".bak"):
        shutil.copy2(path, path + ".bak")
    with open(path, "w") as f:
        json.dump(new, f, indent=2); f.write("\n")
if mode == "add":
    if ours: print("already wired"); sys.exit(0)
    cfg.setdefault("version", 1)
    cfg.setdefault("hooks", {}).setdefault("afterFileEdit", []).append({"command": cmd})
    save(cfg); print("wired")
elif mode == "remove":
    if not ours: print("not wired"); sys.exit(0)
    cfg["hooks"]["afterFileEdit"] = [e for e in entries if e not in ours]
    if not cfg["hooks"]["afterFileEdit"]:
        del cfg["hooks"]["afterFileEdit"]
    save(cfg); print("removed")
PY
}

is_ours() { [ -L "$1" ] && [ "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1")" = "$REPO" ]; }

do_status() {
  for d in "${SKILL_DIRS[@]}"; do
    t="$d/$NAME"
    if [ ! -d "$d" ]; then echo "skip       $d (no such directory)"
    elif is_ours "$t"; then echo "installed  $t -> $REPO"
    elif [ -L "$t" ]; then echo "foreign    $t -> $(readlink "$t")"
    elif [ -e "$t" ]; then echo "conflict   $t (not a symlink)"
    else echo "missing    $t"; fi
  done
  echo "claude     hooks via SKILL.md frontmatter (PostToolUse Write|Edit), active once the skill is invoked; settings.json not modified"
  if [ -d "$HOME/.cursor" ]; then echo "cursor     afterFileEdit $(cursor_json status 2>&1 || echo 'UNREADABLE (invalid JSON)') in $CURSOR_HOOKS"
  else echo "cursor     no ~/.cursor directory"; fi
  [ -f "$DB" ] && echo "database   $DB" || echo "database   MISSING ($DB); run ./install.sh"
  echo "git        core.hooksPath=$(git -C "$REPO" config --get core.hooksPath || echo '(unset)')"
}

do_uninstall() {
  for d in "${SKILL_DIRS[@]}"; do
    t="$d/$NAME"
    if is_ours "$t"; then rm "$t"; echo "removed    $t"; fi
  done
  if [ -d "$HOME/.cursor" ]; then
    out="$(cursor_json remove)" || exit 1
    echo "cursor     $out"
  fi
  if [ -z "${OTS_NO_GIT:-}" ] && [ "$(git -C "$REPO" config --get core.hooksPath || true)" = "hooks" ]; then
    git -C "$REPO" config --unset core.hooksPath && echo "git        core.hooksPath unset"
  fi
}

do_install() {
  # Refuse before changing anything.
  for d in "${SKILL_DIRS[@]}"; do
    t="$d/$NAME"
    if [ -d "$d" ] && [ -e "$t" -o -L "$t" ] && ! is_ours "$t" && [ ! -L "$t" ]; then
      echo "install: refusing to overwrite $t (exists and is not a symlink)" >&2; exit 1
    fi
  done
  if [ ! -f "$DB" ]; then
    echo "Database missing; verifying vendored sources..."
    if ! bash "$REPO/scripts/fetch_sources.sh" --check; then
      echo "install: source verification failed (fetch_sources.sh --check); not building the database" >&2; exit 1
    fi
    python3 "$REPO/scripts/build_db.py"
  fi
  [ -d "$HOME/.gemini" ] && mkdir -p "$ANTIGRAVITY_SKILLS"
  linked_any=0
  for d in "${SKILL_DIRS[@]}"; do
    [ -d "$d" ] && linked_any=1
  done
  [ "$linked_any" = 1 ] || echo "install: no agent skill directories found - nothing linked"
  if [ ! -d "$HOME/.claude/skills" ]; then
    echo "WARNING: $HOME/.claude/skills does not exist; the skill and its Claude validator hook won't be active in Claude Code. Create it (mkdir -p) and re-run install.sh." >&2
  fi
  for d in "${SKILL_DIRS[@]}"; do
    [ -d "$d" ] || continue
    t="$d/$NAME"
    if [ -L "$t" ] && ! is_ours "$t"; then
      echo "skip       $t (symlink to $(readlink "$t"); not ours)"; continue
    fi
    ln -sfn "$REPO" "$t"; echo "linked     $t"
  done
  if [ -d "$HOME/.cursor" ]; then
    out="$(cursor_json add 2>&1)" || { echo "$out" >&2; exit 1; }
    echo "cursor     $out"
  fi
  [ -z "${OTS_NO_GIT:-}" ] && git -C "$REPO" config core.hooksPath hooks 2>/dev/null && echo "git        core.hooksPath=hooks" || true
  echo "claude     hooks come from SKILL.md frontmatter (needs the skill under a skills dir); no settings.json change"
}

case "${1:-}" in
  "") do_install ;;
  --status) do_status ;;
  --uninstall) do_uninstall ;;
  *) echo "usage: install.sh [--status|--uninstall]" >&2; exit 64 ;;
esac
