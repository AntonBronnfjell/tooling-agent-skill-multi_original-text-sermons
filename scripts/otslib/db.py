"""SQLite access: schema, path resolution, connection helpers."""
import os
import sqlite3
import sys
from pathlib import Path

SCHEMA = """
CREATE TABLE words (corpus TEXT, witness TEXT, ref TEXT, pos INTEGER, surface TEXT, lemma TEXT,
                    strongs TEXT, morph TEXT, gloss TEXT, editions TEXT, domain TEXT, syntax_role TEXT);
CREATE TABLE verses (corpus TEXT, witness TEXT, ref TEXT, text TEXT, match_key TEXT);
CREATE TABLE variants (ref TEXT, pos INTEGER, reading TEXT, editions TEXT);
CREATE TABLE lexicon (strongs TEXT, lemma TEXT, lang TEXT, gloss TEXT, definition TEXT);
CREATE TABLE versification (scheme TEXT, source_ref TEXT, canonical_ref TEXT);
CREATE TABLE translations (version TEXT, lang TEXT, ref TEXT, text TEXT);
CREATE TABLE papyri_vocab (lemma TEXT, entry TEXT);
CREATE TABLE meta (key TEXT, value TEXT);
CREATE TABLE order_flags (corpus TEXT, witness TEXT, ref TEXT, reason TEXT);
CREATE INDEX idx_words_cwr ON words (corpus, witness, ref);
CREATE INDEX idx_verses_cwr ON verses (corpus, witness, ref);
CREATE INDEX idx_words_lemma ON words (lemma);
CREATE INDEX idx_words_strongs ON words (strongs);
CREATE INDEX idx_order_flags_cwr ON order_flags (corpus, witness, ref);
"""

MISSING_MSG = "bible.db not found — run ./install.sh or python3 scripts/build_db.py"


def db_path():
    env = os.environ.get("OTS_DB")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "data" / "bible.db"


def connect(path=None):
    conn = sqlite3.connect(str(path or db_path()))
    conn.row_factory = sqlite3.Row
    return conn


def require_db():
    p = db_path()
    if not p.is_file():
        print(MISSING_MSG, file=sys.stderr)
        sys.exit(2)
    return connect(p)
