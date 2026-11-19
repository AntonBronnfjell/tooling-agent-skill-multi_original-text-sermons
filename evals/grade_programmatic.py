#!/usr/bin/env python3
"""Programmatic grading helper for eval runs.

Usage: grade_programmatic.py <run_dir> [--expect TOKEN]... [--forbid TOKEN]... [--db PATH]

<run_dir> holds sermons/*.md and an optional transcript.md. Runs scripts/check_sermon.py on each
sermon and prints JSON:
  {"check_sermon": [{"file", "exit", "errors", "warnings"}...],
   "expect": {TOKEN: {"sermons": bool, "transcript": bool}},
   "forbid": {TOKEN: {"sermons": bool, "transcript": bool}},
   "sermon_files": [...], "has_transcript": bool}
Exit 0 always (grading data, not a gate). Stdlib only.
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

CHECK = Path(__file__).resolve().parent.parent / "scripts" / "check_sermon.py"
LINE = re.compile(r"^(ERROR|WARN)\s+(\d+):\s*(.*)$")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def run_check(path, db=None):
    cmd = [sys.executable, str(CHECK), str(path)] + (["--db", db] if db else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    errors, warnings = [], []
    for ln in (p.stdout + p.stderr).splitlines():
        m = LINE.match(ln.strip().split(": ", 1)[-1]) or LINE.match(ln.strip())
        if m:
            (errors if m.group(1) == "ERROR" else warnings).append(f"{m.group(2)}: {m.group(3)}")
        elif p.returncode == 2 and ln.strip():
            errors.append(ln.strip())
    return {"file": path.name, "exit": p.returncode, "errors": errors, "warnings": warnings}


def grep(tokens, sermon_text, transcript):
    return {t: {"sermons": nfc(t) in sermon_text, "transcript": nfc(t) in transcript} for t in tokens}


def grade(run_dir, expect=(), forbid=(), db=None):
    run_dir = Path(run_dir)
    sermons = sorted((run_dir / "sermons").glob("*.md"))
    tr = run_dir / "transcript.md"
    transcript = nfc(tr.read_text(encoding="utf-8")) if tr.exists() else ""
    sermon_text = nfc("\n".join(s.read_text(encoding="utf-8") for s in sermons))
    return {
        "check_sermon": [run_check(s, db) for s in sermons],
        "expect": grep(expect, sermon_text, transcript),
        "forbid": grep(forbid, sermon_text, transcript),
        "sermon_files": [s.name for s in sermons],
        "has_transcript": tr.exists(),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir")
    ap.add_argument("--expect", action="append", default=[], metavar="TOKEN")
    ap.add_argument("--forbid", action="append", default=[], metavar="TOKEN")
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    json.dump(grade(a.run_dir, a.expect, a.forbid, a.db), sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
