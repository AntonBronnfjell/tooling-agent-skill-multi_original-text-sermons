#!/usr/bin/env python3
"""Lint the skill entrypoint.

Checks SKILL.md at the skill root (default: this repo; or the path given):
- YAML frontmatter with `name: original-text-sermons` and a non-empty `description` of <= 1024 chars
  (other keys, e.g. `hooks`, are allowed);
- fewer than 500 lines;
- every relative markdown link (outside code fences) resolves to an existing file or directory;
- every `scripts/<name>.py|.sh` named anywhere in SKILL.md exists.

Usage: lint_skill.py [ROOT]
Exit: 0 clean, 1 on any failure (one `ERROR: ...` line per problem).
"""
import re
import sys
from pathlib import Path

NAME = "original-text-sermons"
MAX_DESC = 1024
MAX_LINES = 500
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCRIPT_RE = re.compile(r"(?<![\w.-])(scripts/[\w./-]+?\.(?:py|sh))(?![\w])")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


def frontmatter(text):
    """Return ({key: value}, {keys whose value is an unquoted one-line scalar}) for top-level
    frontmatter keys, or None if there is no frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    out, plain, key = {}, set(), None
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in (">", "|", ">-", "|-", ">+", "|+"):
                val = ""
            elif len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            elif val and val[0] not in "{[":  # flow collections (e.g. `hooks: {...}`) may hold colons
                plain.add(key)
            out[key] = val
        elif key and line.startswith((" ", "\t")):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out, plain


def lint(root):
    root = Path(root)
    skill = root / "SKILL.md"
    if not skill.is_file():
        return [f"SKILL.md not found in {root}"]
    text = skill.read_text(encoding="utf-8")
    errors = []

    parsed = frontmatter(text)
    if parsed is None:
        errors.append("SKILL.md has no YAML frontmatter (--- ... ---) at the top")
    else:
        fm, plain = parsed
        for k in sorted(plain):
            if ": " in fm[k] or " #" in fm[k]:
                errors.append(f"frontmatter {k}: unquoted value contains a colon+space or ' #' "
                              "(invalid YAML plain scalar): quote it or rephrase")
        if fm.get("name") != NAME:
            errors.append(f"frontmatter name must be '{NAME}', got {fm.get('name')!r}")
        desc = fm.get("description", "")
        if not desc:
            errors.append("frontmatter description is missing or empty")
        elif len(desc) > MAX_DESC:
            errors.append(f"frontmatter description is {len(desc)} chars (max {MAX_DESC})")

    n = len(text.splitlines())
    if n >= MAX_LINES:
        errors.append(f"SKILL.md has {n} lines (must be < {MAX_LINES})")

    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(line):
            if EXTERNAL.match(target):
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            if path and not (root / path).exists():
                errors.append(f"line {no}: link target does not exist: {path}")

    for script in sorted(set(SCRIPT_RE.findall(text))):
        if not (root / script).is_file():
            errors.append(f"script named in SKILL.md does not exist: {script}")
    return errors


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    errors = lint(root)
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print(f"OK: {root / 'SKILL.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
