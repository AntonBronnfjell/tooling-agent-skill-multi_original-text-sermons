#!/usr/bin/env python3
"""Build data/bible.db from the vendored (xz-compressed) sources."""
import argparse
import contextlib
import hashlib
import importlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from otslib import db  # noqa: E402

LOADERS = ["stepbible", "versification", "macula", "greek_editions", "lxx", "dss", "ext", "translations"]


def build(sources_dir, db_file, only=None, out=sys.stdout):
    sources_dir, db_file = Path(sources_dir), Path(db_file)
    todo = only or LOADERS
    unknown = [n for n in todo if n not in LOADERS]
    if unknown:
        raise SystemExit(f"unknown loader(s): {', '.join(unknown)} (known: {', '.join(LOADERS)})")
    db_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = db_file.with_name(db_file.name + f".tmp{os.getpid()}")
    tmp.unlink(missing_ok=True)
    conn = db.connect(tmp)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript(db.SCHEMA)
        for name in [n for n in LOADERS if n in todo]:
            t0 = time.time()
            mod = importlib.import_module(f"loaders.{name}")  # missing loader module = hard error
            with contextlib.redirect_stdout(out):  # loaders print their stats; keep them on `out`
                n = mod.load(conn, sources_dir)
            conn.commit()
            print(f"{name}: {n} rows ({time.time() - t0:.1f}s)", file=out)
        manifest = sources_dir / "MANIFEST.json"
        digest = hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.is_file() else ""
        conn.executemany("INSERT INTO meta VALUES (?, ?)", [
            ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("manifest_sha256", digest)])
        conn.commit()
        conn.close()
        os.replace(tmp, db_file)
    except BaseException:
        conn.close()
        tmp.unlink(missing_ok=True)
        raise
    return db_file


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", type=Path, default=HERE.parent / "sources")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--only", help="comma-separated loaders to run (default: all)")
    a = ap.parse_args(argv)
    only = [s.strip() for s in a.only.split(",") if s.strip()] if a.only else None
    if only and a.db is None:
        print(f"--only builds a partial DB (only {', '.join(only)}); writing it over the default {db.db_path()} "
              "would leave the skill without the other corpora. Pass --db PATH for a partial build, or omit "
              "--only to rebuild everything.", file=sys.stderr)
        return 2
    dest = build(a.sources, a.db or db.db_path(), only)
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
