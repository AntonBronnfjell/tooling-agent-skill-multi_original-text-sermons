#!/usr/bin/env bash
# Post-write hook: validate sermon files with scripts/check_sermon.py.
# Reads hook JSON on stdin: Claude Code {"tool_input":{"file_path":...}} or Cursor {"file_path":...}.
# - not a */sermons/*.md path, or unparseable JSON ......... exit 0, silent
# - validator finds errors (exit 1) ....................... output on stderr, exit 2 (fed back to the model)
# - DB missing/invalid (validator exit 2) ................. message on stderr, exit 0 (never block writes)
# - warnings only (Claude Code payload) ................... exit 0 with JSON on stdout:
#   {"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<warnings>"}}
#   (Claude Code reads stdout JSON only on exit 0; additionalContext reaches the model next to the tool result)
# - warnings only (Cursor payload) ........................ warnings on stderr, exit 0
# - clean ................................................. exit 0, silent (the validator's `OK <file>` is dropped)
set -u

SRC="${BASH_SOURCE[0]}"
REPO="$(python3 -c 'import os,sys; print(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[1]))))' "$SRC")"

PARSED="$(python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input")
    p = (ti.get("file_path") if isinstance(ti, dict) else None) or d.get("file_path") or ""
    shape = "claude" if isinstance(ti, dict) else "cursor"
    print(shape + "\t" + (p if isinstance(p, str) else ""))
except Exception:
    pass
' 2>/dev/null)"
SHAPE="${PARSED%%$'\t'*}"
FILE="${PARSED#*$'\t'}"

case "$FILE" in
  */sermons/*.md) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

OUT="$(python3 "$REPO/scripts/check_sermon.py" "$FILE" 2>&1)"
RC=$?
OUT="$(printf '%s\n' "$OUT" | grep -v '^OK ')"
case "$RC" in
  0)
    [ -n "$OUT" ] || exit 0
    if [ "$SHAPE" = "claude" ]; then
      python3 -c 'import json, sys
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
      "additionalContext": "check_sermon.py warnings for " + sys.argv[1] + ":\n" + sys.argv[2]}}))' "$FILE" "$OUT"
    else
      printf '%s\n' "$OUT" >&2
    fi
    exit 0 ;;
  1) printf '%s\n' "$OUT" >&2; exit 2 ;;
  2) printf 'original-text-sermons: sermon not validated (database missing or invalid). Run install.sh.\n%s\n' "$OUT" >&2; exit 0 ;;
  *) printf '%s\n' "$OUT" >&2; exit 0 ;;
esac
