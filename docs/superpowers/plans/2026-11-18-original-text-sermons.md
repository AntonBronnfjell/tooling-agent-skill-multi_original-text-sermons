# original-text-sermons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A portable agent skill that writes concise sermons from vendored Hebrew/Aramaic/Greek source data, with mechanically verified quotes, linguistic checks, translation comparison, hooks and evals.

**Architecture:** Raw sources vendored compressed under `sources/` (pinned in `MANIFEST.json`). `scripts/build_db.py` loads them through one loader module per source family into `data/bible.db` (SQLite). `scripts/lookup.py` queries it; `scripts/check_sermon.py` validates sermon files. `SKILL.md` + `references/` + `templates/` steer the model. Repo root is the skill root; `install.sh` symlinks it into agent skill dirs.

**Tech Stack:** Python 3 stdlib only (`sqlite3`, `csv`, `xml.etree`, `unicodedata`, `json`, `lzma`, `unittest`), Bash, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-18-original-text-sermons-design.md`

## Global Constraints

- Python 3 standard library only. No pip installs, tests use `unittest` (`python3 -m unittest discover -s tests -v`).
- Repo root = skill root; `SKILL.md` at root, < 500 lines, frontmatter `name: original-text-sermons`.
- Every source file vendored under `sources/` is compressed (`.xz`), each file < 100 MB, repo target < 500 MB; every one listed in `sources/MANIFEST.json` with `upstream`, `commit_or_version`, `sha256`, `license_note`.
- `data/bible.db` and `sources/user/` are gitignored. DB path: `$OTS_DB` if set, else `<repo>/data/bible.db` resolved through symlinks.
- Canonical refs: `Book.Chapter.Verse` with English (KJV) versification and book IDs `Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev` (OSIS). Single-chapter ranges allowed: `John.3.16-17`.
- Quote tag grammar: `[CORPUS[:WITNESS] Ref]`; corpora `HEB ARC GRC LXX DSS EXT`; defaults `GRC→SBL`, `HEB/ARC→WLC`, `LXX→Rahlfs`; `DSS` and `EXT` require a witness.
- Corpus keys in DB: `hebot` (HEB+ARC), `grnt`, `lxx`, `dss`, `ext`.
- No doctrine sources: no creeds, commentaries, study-Bible notes, unfoldingWord notes, church fathers.
- Evals assert evidence/options shown, never a doctrinal conclusion.
- Sermons written to `./sermons/YYYY-MM-DD-<slug>.<lang>.md` in the user's cwd.

## Review Focus

1. Spanish/abbreviated/chapter-only refs (`Juan 3:16`, `1 Jn 5:7`, `Jn 3`) — expected: parsed or a clear "unknown ref" message, never a traceback. Test in Task 1.
2. A verse absent from the default witness (Acts 8:37 not in SBL, present in TR/Byz) — expected: lookup says which witnesses have it; validator rejects `[GRC Acts.8.37]` but accepts `[GRC:TR Acts.8.37]`. Tests in Tasks 3, 9, 11.
3. Hebrew/LXX vs English versification (Mal.4.1 = Heb Mal 3:19; Eng Ps.51.1 = Heb 51:3 = LXX Ps 50:3) — expected: canonical English ref returns the right Hebrew/LXX words. Test in Task 4.
4. Quotes with `…` elision or spanning a verse range — expected: segments matched in order within the range. Test in Task 11.
5. Fresh clone / DB missing — expected: every script prints `bible.db not found — run ./install.sh or python3 scripts/build_db.py` and exits 2. Test in Task 3.

---

### Task 1: Scaffold, refs and normalization

**Files:**
- Create: `.gitignore`, `scripts/otslib/__init__.py`, `scripts/otslib/refs.py`, `scripts/otslib/norm.py`, `tests/__init__.py`, `tests/test_refs.py`, `tests/test_norm.py`

**Interfaces:**
- Produces:
  - `refs.parse_ref(text: str) -> Ref` — `Ref = NamedTuple(book: str, chapter: int, verse: int | None, verse_end: int | None)`; accepts OSIS (`John.3.16`), English/Spanish names and common abbreviations (`Juan 3:16`, `1 Jn 5:7`, `Jn 3`, `Mateo 16:18`, `Salmos 51`), ranges `3:16-17`. Raises `RefError(msg)` for unknown book.
  - `refs.to_osis(ref: Ref) -> str` (`"John.3.16"`, `"John.3.16-17"`, `"John.3"`).
  - `refs.BOOKS: list[str]` (canonical order, Global Constraints list).
  - `norm.nfc(s) -> str`; `norm.display(s, lang) -> str` (Hebrew: strip cantillation U+0591–U+05AF and meteg U+05BD, keep vowels; Greek unchanged); `norm.match_key(s, lang) -> str` (display + NFC, drop punctuation `.,;·:׃׀` and `־`→space, collapse whitespace, Greek `casefold`); `norm.strip_accents(s) -> str` (remove all combining marks — used only for EXT form search).
  - `tests/__init__.py` inserts `scripts/` on `sys.path`.

- [ ] **Step 1: Write failing tests**

```python
class RefTests(unittest.TestCase):
    def test_osis(self): self.assertEqual(to_osis(parse_ref("John.3.16")), "John.3.16")
    def test_spanish(self): self.assertEqual(to_osis(parse_ref("Juan 3:16")), "John.3.16")
    def test_abbrev(self): self.assertEqual(to_osis(parse_ref("1 Jn 5:7")), "1John.5.7")
    def test_chapter_only(self): self.assertEqual(to_osis(parse_ref("Jn 3")), "John.3")
    def test_range(self): self.assertEqual(to_osis(parse_ref("Juan 3:16-17")), "John.3.16-17")
    def test_psalms_es(self): self.assertEqual(to_osis(parse_ref("Salmos 51:1")), "Ps.51.1")
    def test_unknown(self):
        with self.assertRaises(RefError): parse_ref("Hezekiah 1:1")

class NormTests(unittest.TestCase):
    def test_hebrew_cantillation_removed(self):
        self.assertEqual(display("בְּרֵאשִׁ֖ית", "heb"), "בְּרֵאשִׁית")
    def test_greek_match_key(self):
        self.assertEqual(match_key("Καὶ θεὸς ἦν ὁ λόγος.", "grc"), match_key("καὶ θεὸς ἦν ὁ λόγος", "grc"))
    def test_maqaf(self):
        self.assertEqual(match_key("כָּל־הָאָרֶץ", "heb"), match_key("כָּל הָאָרֶץ", "heb"))
```

- [ ] **Step 2:** `python3 -m unittest tests.test_refs tests.test_norm -v` — Expected: FAIL (ImportError).
- [ ] **Step 3:** Implement `refs.py` (book alias table: OSIS, English full + SBL abbreviations, Spanish full + common abbreviations, all matched case-/accent-insensitively) and `norm.py`.
- [ ] **Step 4:** Re-run — Expected: PASS.
- [ ] **Step 5:** `.gitignore`: `data/`, `sources/user/`, `__pycache__/`, `sermons/`. Commit `feat: add ref parsing and text normalization`.

---

### Task 2: Vendor sources

**Files:**
- Create: `scripts/fetch_sources.sh`, `sources/MANIFEST.json`, `sources/**.xz`, `tests/fixtures/sources/**` (small excerpts)

**Interfaces:**
- Produces: vendored files at these paths (loaders in Tasks 3–8 read them via `lzma.open`):
  - `sources/stepbible/TAHOT_*.txt.xz`, `TAGNT_*.txt.xz`, `TBESH.txt.xz`, `TBESG.txt.xz`, `TVTMS.txt.xz` — STEPBible-Data (github.com/STEPBible/STEPBible-Data)
  - `sources/macula/macula-greek-SBLGNT.tsv.xz`, `macula-hebrew.tsv.xz` — Clear-Bible/macula-greek, Clear-Bible/macula-hebrew (TSV exports, not XML)
  - `sources/lxx/` — tagged Rahlfs (eliranwong/LXX-Rahlfs-1935, CATSS-derived morphology); if unusable, Swete (eliranwong/LXX-Swete-1930) and set witness `Swete`
  - `sources/dss/*.tf.xz` — ETCBC/dss Text-Fabric features needed: `otype oslots glyph lex scroll book chapter verse` (biblical only)
  - `sources/ext/josephus/*.xml.xz` (Perseus canonical-greekLit `tlg0526`), `sources/ext/philo/*.xml.xz` (First1KGreek `tlg0018`)
  - `sources/ext/moulton-milligan.txt.xz` — only if a usable OCR text exists (archive.org); else MANIFEST entry `"status": "deferred"`
  - `sources/translations/<version>.vpl.xz` — eBible.org VPL: `KJV YLT BSB WEB` (en), `RV1909` (es), `Reina1569` (es, if available else omitted)
- `fetch_sources.sh [--check]`: downloads each MANIFEST entry at its pinned commit/version, xz-compresses, writes sha256; `--check` verifies hashes only, no network.

- [ ] **Step 1:** Write `MANIFEST.json` entries (one per file, pinned to the current upstream commit hash/version), then `fetch_sources.sh` driven by it.
- [ ] **Step 2:** Run `bash scripts/fetch_sources.sh` — Expected: all non-deferred files present; `du -sh sources` < 500M; `find sources -size +100M` empty. If any file exceeds 100 MB, split it by book range (as STEPBible already does) — no Git LFS.
- [ ] **Step 3:** Run `bash scripts/fetch_sources.sh --check` — Expected: `OK` per file, exit 0.
- [ ] **Step 4:** Create `tests/fixtures/sources/` excerpts mirroring the same relative paths (uncompressed, few KB each), cut from the real files, covering: Gen.1.1–2, Ps.51.1–3, Mal.3.19/4.1, Isa.45.21–25, Isa.53.11, Matt.16.18, John.1.1, John.3.16–17, Acts.2.4, Acts.2.38, Acts.8.36–38, Gal.2.16, Phil.2.10–11, 1John.5.7–8; plus the TVTMS rows for those refs, lexicon rows for their lemmas, one Josephus section containing ἐκκλησία, 1QIsaᵃ Isa 53:11.
- [ ] **Step 5:** Commit `chore: vendor pinned original-language sources` (sources + fixtures separately committed is fine).

---

### Task 3: DB schema, build_db, STEPBible loader

**Files:**
- Create: `scripts/otslib/db.py`, `scripts/build_db.py`, `scripts/loaders/__init__.py`, `scripts/loaders/stepbible.py`, `tests/test_build_stepbible.py`

**Interfaces:**
- Consumes: `refs`, `norm` (Task 1); fixture/vendored paths (Task 2).
- Produces:
  - `db.db_path() -> Path`; `db.connect(path=None) -> sqlite3.Connection` (row_factory=Row); `db.require_db() -> sqlite3.Connection` — prints the Review Focus #5 message to stderr and `sys.exit(2)` if missing.
  - `db.SCHEMA: str` creating:
    - `words(corpus, witness, ref, pos INTEGER, surface, lemma, strongs, morph, gloss, editions, domain, syntax_role)`
    - `verses(corpus, witness, ref, text, match_key)` — `text` = `norm.display`, `match_key` = `norm.match_key`; one row per corpus+witness+ref
    - `variants(ref, pos INTEGER, reading, editions)`
    - `lexicon(strongs, lemma, lang, gloss, definition)`
    - `versification(scheme, source_ref, canonical_ref)`
    - `translations(version, lang, ref, text)`
    - `papyri_vocab(lemma, entry)`
    - `meta(key, value)` — `built_at`, `manifest_sha256`
    - indexes on `(corpus, witness, ref)`, `words(lemma)`, `words(strongs)`.
  - `build_db.py [--sources DIR] [--db PATH] [--only LOADER,...]` — calls each loader's `load(conn, sources_dir: Path) -> int` (rows inserted) in order `stepbible, versification, macula, lxx, dss, ext, translations`; builds into a temp file then atomically renames.
  - `stepbible.load(conn, sources_dir)`: TAHOT → `words`/`verses` corpus `hebot`, witness `WLC` (+ `Qere` rows where Ketiv/Qere differ); TAGNT → `words` with `editions` string; `verses` corpus `grnt` built per witness `SBL NA THGNT WH Byz TR` from the words whose editions include it; `variants` for words not in all editions; TBESH/TBESG → `lexicon`. Map columns by the header names in the files, not by index.

- [ ] **Step 1: Write failing tests** (build from `tests/fixtures/sources` into a temp DB in `setUpClass`)

```python
def test_sbl_john_1_1(self):
    row = q("select text from verses where corpus='grnt' and witness='SBL' and ref='John.1.1'")
    self.assertIn("θεὸς ἦν ὁ λόγος", row["text"])
def test_acts_8_37_absent_in_sbl_present_in_tr(self):
    self.assertIsNone(q("select 1 from verses where corpus='grnt' and witness='SBL' and ref='Acts.8.37'"))
    self.assertIsNotNone(q("select 1 from verses where corpus='grnt' and witness='TR' and ref='Acts.8.37'"))
def test_comma_only_late(self):
    sbl = q("select text from verses where corpus='grnt' and witness='SBL' and ref='1John.5.7'")["text"]
    self.assertNotIn("πατήρ", sbl)
def test_hebrew_display_no_cantillation(self):
    t = q("select text from verses where corpus='hebot' and witness='WLC' and ref='Gen.1.1'")["text"]
    self.assertFalse(any(0x0591 <= ord(c) <= 0x05AF for c in t))
def test_lexicon_has_ekklesia(self):
    self.assertIsNotNone(q("select 1 from lexicon where lemma='ἐκκλησία'"))
def test_missing_db_exit_2(self):
    r = subprocess.run([sys.executable, "scripts/lookup.py", "verse", "John.1.1"], env={**os.environ, "OTS_DB": "/nonexistent.db"}, capture_output=True, text=True)
    self.assertEqual(r.returncode, 2); self.assertIn("bible.db not found", r.stderr)
```

(`test_missing_db_exit_2` stays skipped until Task 9 creates `lookup.py`: `@unittest.skipUnless(Path("scripts/lookup.py").exists(), ...)`.)

- [ ] **Step 2:** `python3 -m unittest tests.test_build_stepbible -v` — Expected: FAIL.
- [ ] **Step 3:** Implement `db.py`, `build_db.py`, `loaders/stepbible.py`.
- [ ] **Step 4:** Re-run — Expected: PASS. Then full build `python3 scripts/build_db.py` — Expected: completes, prints row counts per loader (grnt words ≈ 140k, hebot words ≈ 300k+).
- [ ] **Step 5:** Commit `feat: build SQLite DB from STEPBible data`.

---

### Task 4: Versification

**Files:**
- Create: `scripts/loaders/versification.py`, `tests/test_versification.py`
- Modify: `scripts/otslib/refs.py` (add `canonical(conn, scheme: str, source_ref: str) -> str` and `source_ref(conn, scheme: str, canonical_ref: str) -> str`)

**Interfaces:**
- Consumes: `db.SCHEMA` `versification` table.
- Produces: rows for schemes `hebrew` and `lxx` mapping to canonical English refs; refs with no mapping row are identity. Loaders in Tasks 3 (TAHOT), 6 (LXX, DSS) store `ref` as canonical English — TAHOT already gives English refs with Hebrew in brackets (`Mal.4.1(3.19)`): store the English one.

- [ ] **Step 1: Failing tests**

```python
def test_mal(self): self.assertEqual(canonical(c, "hebrew", "Mal.3.19"), "Mal.4.1")
def test_ps51_hebrew(self): self.assertEqual(canonical(c, "hebrew", "Ps.51.3"), "Ps.51.1")
def test_ps51_lxx(self): self.assertEqual(canonical(c, "lxx", "Ps.50.3"), "Ps.51.1")
def test_identity(self): self.assertEqual(canonical(c, "lxx", "Gen.1.1"), "Gen.1.1")
def test_tahot_stored_english(self):
    self.assertIsNotNone(q("select 1 from verses where corpus='hebot' and ref='Mal.4.1'"))
```

- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Implement: parse TVTMS rows for Hebrew→English and Greek(LXX)→English; skip rows that don't parse, print skipped count. `# ponytail: only hebrew/lxx schemes; add Vulgate etc. if ever needed`.
- [ ] **Step 4:** Run — PASS.
- [ ] **Step 5:** Commit `feat: add versification mapping`.

---

### Task 5: MACULA enrichment

**Files:**
- Create: `scripts/loaders/macula.py`, `tests/test_macula.py`

**Interfaces:**
- Consumes: `words` rows from Task 3.
- Produces: fills `words.domain` (Louw-Nida for Greek, SDBH for Hebrew) and `words.syntax_role` (MACULA `role`/clause info) on existing `grnt` (witness SBL rows) and `hebot` (WLC) rows. Join key: `(ref, lemma normalized by norm.strip_accents, nth occurrence of that lemma in the verse)`. Unmatched rows stay NULL; loader prints match rate (expect > 95%).

- [ ] **Step 1: Failing tests**

```python
def test_logos_domain(self):
    r = q("select domain from words where corpus='grnt' and ref='John.1.1' and lemma='λόγος' limit 1")
    self.assertTrue(r["domain"])
def test_hebrew_role(self):
    self.assertTrue(q("select syntax_role from words where corpus='hebot' and ref='Gen.1.1' and syntax_role is not null limit 1"))
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS; full build prints match rate ≥ 95%.
- [ ] **Step 5:** Commit `feat: enrich words with MACULA domains and syntax`.

---

### Task 6: LXX and Dead Sea Scrolls

**Files:**
- Create: `scripts/loaders/lxx.py`, `scripts/loaders/dss.py`, `scripts/otslib/tf.py`, `tests/test_lxx_dss.py`

**Interfaces:**
- Consumes: `refs.canonical` (Task 4).
- Produces:
  - `lxx.load`: `words`/`verses` corpus `lxx`, witness `Rahlfs` (or `Swete`), refs canonical English.
  - `tf.read_feature(path) -> dict[int, str]` — minimal Text-Fabric `.tf` reader (header `@` lines, blank line, then `value` / `node\tvalue` / `a-b\tvalue` lines with implicit node increment); `tf.read_oslots(path) -> dict[int, list[int]]`.
  - `dss.load`: biblical words only (`book` feature present) → `words`/`verses` corpus `dss`, witness = `scroll` siglum without punctuation (`1QIsaa`), refs canonical English via `hebrew` scheme.

- [ ] **Step 1: Failing tests**

```python
def test_lxx_isa_45_23_theo(self):
    t = q("select text from verses where corpus='lxx' and ref='Isa.45.23'")["text"]
    self.assertIn("θεῷ", t)
def test_lxx_ps_mapped(self):
    self.assertIsNotNone(q("select 1 from verses where corpus='lxx' and ref='Ps.51.1'"))
def test_dss_1qisaa(self):
    self.assertIsNotNone(q("select 1 from verses where corpus='dss' and witness='1QIsaa' and ref='Isa.53.11'"))
def test_tf_range_line(self):
    self.assertEqual(read_feature(fixture("range.tf"))[3], "x")  # fixture: '@node\n\n1-3\tx\n'
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS.
- [ ] **Step 5:** Commit `feat: load LXX and biblical Dead Sea Scrolls`.

---

### Task 7: Josephus, Philo, Moulton-Milligan

**Files:**
- Create: `scripts/loaders/ext.py`, `tests/test_ext.py`

**Interfaces:**
- Produces:
  - `words`/`verses` corpus `ext`, witness `Josephus` | `Philo`, `ref` = `<WorkAbbrev>.<book>.<section>` from TEI `div[@type='textpart']/@n` nesting (Josephus works: `Ant`, `War`, `Life`, `Ag.Ap.`→`AgAp`; Philo: Perseus/First1K work abbreviations, recorded in a dict in `ext.py`). `lemma` NULL (TEI has none); `surface` = token.
  - `papyri_vocab(lemma, entry)` from Moulton-Milligan if vendored (split entries on headword lines); skipped with a message if MANIFEST marks it deferred.

- [ ] **Step 1: Failing tests**

```python
def test_josephus_section_has_ekklesia(self):
    self.assertIsNotNone(q("select 1 from words where corpus='ext' and witness='Josephus' and surface like 'ἐκκλησ%'"))
def test_ext_ref_format(self):
    r = q("select ref from verses where corpus='ext' and witness='Josephus' limit 1")["ref"]
    self.assertRegex(r, r"^[A-Za-z]+\.\d+\.\d+$")
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS.
- [ ] **Step 5:** Commit `feat: load Josephus, Philo and papyri vocabulary`.

---

### Task 8: Comparison translations

**Files:**
- Create: `scripts/loaders/translations.py`, `tests/test_translations.py`, `sources/user/README.md` (format doc; file itself gitignored except README — add `!sources/user/README.md` to `.gitignore`)

**Interfaces:**
- Produces: `translations` rows from `sources/translations/*.vpl.xz` (version = filename stem, lang from MANIFEST) and from `sources/user/*.csv` (header `ref,text`, first line comment `# version=RVR1960 lang=es`; `ref` any form `parse_ref` accepts).

- [ ] **Step 1: Failing tests**

```python
def test_kjv(self): self.assertIn("Word was God", q("select text from translations where version='KJV' and ref='John.1.1'")["text"])
def test_rv1909(self): self.assertIsNotNone(q("select 1 from translations where version='RV1909' and ref='John.1.1'"))
def test_user_csv(self):  # fixture tests/fixtures/sources/user/TEST.csv with '# version=TEST lang=es' and 'Juan 1:1,En el principio...'
    self.assertIsNotNone(q("select 1 from translations where version='TEST' and ref='John.1.1'"))
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS.
- [ ] **Step 5:** Commit `feat: load comparison translations and user CSVs`.

---

### Task 9: lookup.py

**Files:**
- Create: `scripts/lookup.py`, `tests/test_lookup.py`

**Interfaces:**
- Consumes: everything above.
- Produces CLI (`--format json|text`, default json; `--db PATH`):
  - `verse <ref> [--corpus grnt|hebot|lxx|dss|ext] [--witness W]` → `{ref, corpus, witness, text, words:[{pos,surface,lemma,strongs,morph,gloss,domain,syntax_role}]}`; corpus defaults by book (OT→hebot, NT→grnt). If absent in requested witness → `{ref, absent_in: W, present_in: [...]}` exit 0.
  - `interlinear <ref>` → words with gloss only.
  - `variants <ref>` → `[{pos, reading, editions, class: "early"|"late"}]` — `late` iff editions ⊆ {TR, Byz}.
  - `word <lemma|strongs>` → lexicon + domain + NT count + LXX: Hebrew lemmas it renders, found by aligning LXX and hebot words at same ref with matching Strong's/gloss — `# ponytail: same-verse co-occurrence, not true alignment`.
  - `usage <lemma>` → counts + up to 5 contexts each for grnt, lxx, ext (ext matched by `strip_accents` on all surface forms of that lemma seen in grnt+lxx) + `papyri` entry or `null`.
  - `compare <ref> [--versions V,...]` → `{original, versions:{V: text}}`.
  - `dss <ref>`, `lxx <ref>` → reading(s) + word-level diff against hebot (`difflib.SequenceMatcher` on `match_key` tokens).
  - `search <lemma> [--corpus]` → refs.
  - Unknown ref → stderr `unknown ref: ...`, exit 1.

- [ ] **Step 1: Failing tests** (subprocess against fixture DB)

```python
def test_verse_json(self): self.assertEqual(run("verse", "Juan 1:1")["ref"], "John.1.1")
def test_absent_witness(self):
    out = run("verse", "Acts.8.37", "--witness", "SBL")
    self.assertEqual(out["absent_in"], "SBL"); self.assertIn("TR", out["present_in"])
def test_comma_variant_late(self):
    self.assertTrue(any(v["class"] == "late" for v in run("variants", "1John.5.7")))
def test_compare(self): self.assertIn("KJV", run("compare", "John.1.1")["versions"])
def test_usage_ekklesia_has_ext(self): self.assertGreater(run("usage", "ἐκκλησία")["counts"]["ext"], 0)
def test_dss_diff(self): self.assertTrue(run("dss", "Isa.53.11")["readings"])
def test_unknown_ref_exit_1(self): self.assertEqual(run_raw("verse", "Hezekiah 1:1").returncode, 1)
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS (incl. Task 3's now-unskipped `test_missing_db_exit_2`).
- [ ] **Step 5:** Commit `feat: add lookup CLI`.

---

### Task 10: References and templates

**Files:**
- Create: `references/fidelity-rules.md`, `linguistics-greek.md`, `linguistics-hebrew.md`, `exegetical-fallacies.md`, `translation-comparison.md`, `text-criticism.md`, `tradition-vocabulary.md`, `contested-readings.md`, `specializations.md`, `audiences.md`; `templates/big-idea.md`, `templates/hook-book-look-took.md`, `templates/sermon-output.md`; `scripts/otslib/references.py`; `tests/test_references.py`

**Interfaces:**
- Produces `references.tradition_terms(lang: str) -> set[str]`, `references.contested_refs() -> set[str]`, `references.template_sections(name: str) -> list[str]` parsing these machine-read tables:
  - `tradition-vocabulary.md`: one table `| lang | term | plain rendering | note |`, ≥ 20 rows each for `en` and `es` (e.g. en church→assembly, baptize→immerse, Holy Ghost→holy spirit, Godhead, Trinity, sacrament, rapture; es iglesia→asamblea, bautizar→sumergir, Espíritu Santo→espíritu santo, Trinidad, sacramento). Builder curates the rest; every term must be one the text never literally says. Terms are the left column only.
  - `contested-readings.md`: table `| ref | issue | options |` — at least John.1.1, Gal.2.16, Gen.1.26, Acts.2.38, 1John.5.7, Matt.28.19, Isa.9.6, Phil.2.6, Titus.2.13, Rom.9.5, Col.2.9, Deut.6.4.
- Prose content requirements:
  - `fidelity-rules.md`: never quote from memory; two-layer translation; options for contested readings; capitalization rule (spec 9); usage claims only from `lookup.py` output; no doctrine sources; 1st-century background allowed, Philo allegory not.
  - `linguistics-greek.md`: aspect (aorist ≠ once-for-all; present ≠ always continuous), voice incl. middle, article (Colwell — contested, show options), genitive categories (*pistis Christou*), participles, conditional classes, word order emphasis, Semitisms, LXX as lexicon.
  - `linguistics-hebrew.md`: wayyiqtol/qatal/yiqtol, construct chains, parallelism, idioms, hendiadys, divine names (YHWH, Elohim plural form), *hesed* range, Ketiv/Qere.
  - `exegetical-fallacies.md`: root, etymological, totality transfer, anachronism (dynamite), word-concept, selective evidence, overspecification — each with a wrong/right example.
  - `translation-comparison.md`: divergence classes `added-words harmonization capitalization tradition-vocabulary late-reading paraphrase`; how to report.
  - `text-criticism.md`: early vs late, how to use `variants`/`dss`/`lxx`, reporting format.
  - `specializations.md`: theology, apologetics (each point answers an objection), evangelistic (clear call to respond), teaching/discipleship, pastoral.
  - `audiences.md`: christian, non-christian (no unexplained insider terms; list of terms to explain), mixed.
  - Templates: frontmatter `sections:` as in Task 10 + per-section guidance; `sermon-output.md` = full example sermon file (John 3:16–17, `es`) that passes `check_sermon.py`.

- [ ] **Step 1: Failing test**

```python
def test_tables_parse(self):
    self.assertGreaterEqual(len(tradition_terms("en")), 20); self.assertGreaterEqual(len(tradition_terms("es")), 20)
    self.assertIn("John.1.1", contested_refs())
def test_template_sections(self):
    self.assertEqual(template_sections("hook-book-look-took"), ["Hook", "Book", "Look", "Took", "Notes"])
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Write files. **Step 4:** Run — PASS; also all quotes in `references/*.md` examples use tag syntax only where the text is real (spot-check with `check_sermon.py`-style `lookup.py verse`).
- [ ] **Step 5:** Commit `docs: add fidelity, linguistics and template references`.

---

### Task 11: check_sermon.py + validator fixtures

**Files:**
- Create: `scripts/check_sermon.py`, `tests/test_check_sermon.py`, `evals/fixtures/positive/*.md`, `evals/fixtures/negative/*.md`
- Consumes: `references/tradition-vocabulary.md`, `references/contested-readings.md`, `templates/*.md` (Task 10) via `references.tradition_terms(lang)` / `references.contested_refs()`.

**Interfaces:**
- Produces: `check_sermon.py <file>... [--db PATH]` → per-file lines `ERROR <line>: <msg>` / `WARN <line>: <msg>`; exit 1 if any ERROR, else 0. Library: `check(path: Path, conn) -> list[Finding]`, `Finding = NamedTuple(level, line, msg)`.
- Frontmatter: `---` block of `key: value` lines (no YAML lib). Required keys: `passage language specialization audience template date`. `template` = name of a file in `templates/` (minus `.md`) or `custom`; `custom` requires `sections: A, B, C`.
- Template files declare required sections in their own frontmatter `sections: Introduction, Text, Big Idea, Point 1, Point 2, Point 3, Conclusion, Notes` (big-idea) / `sections: Hook, Book, Look, Took, Notes` (hook-book-look-took). Section present = `## <name>` heading (prefix match, so `## Point 1 — …` counts).
- Quote block: `> [TAG Ref] original` followed by `> Literal: …` and `> Natural: …`.
- Rules (spec 7.7): quote segments (split on `…`) each found in order in the concatenated `match_key` of the ref range for corpus+witness; tradition terms (case-insensitive whole word, language from frontmatter) are errors on `Literal:`/`Natural:` lines only; warnings: body word count (excluding quote blocks and `## Notes`) outside 500–1300; any ref in `contested-readings.md` quoted while `## Notes` doesn't mention that ref.

- [ ] **Step 1: Failing tests**

```python
def test_positive_fixtures_pass(self):
    for f in POS: self.assertFalse([x for x in check(f, c) if x.level == "ERROR"], f)
def test_misquote(self): self.assertIn("not found", msgs("negative/misquote.md"))           # altered Greek in John.1.1
def test_tr_as_default(self): self.assertIn("not found", msgs("negative/comma-as-sbl.md"))   # [GRC 1John.5.7] with Comma text
def test_tr_tagged_ok(self): self.assertNotIn("not found", msgs("positive/comma-tagged-tr.md"))
def test_dss_requires_witness(self): self.assertIn("requires a witness", msgs("negative/dss-no-witness.md"))
def test_tradition_term_on_natural(self): self.assertIn("tradition term", msgs("negative/church-in-natural.md"))
def test_tradition_term_in_prose_ok(self): self.assertNotIn("tradition term", msgs("positive/church-in-prose.md"))
def test_ellipsis_and_range(self): self.assertFalse(errors("positive/ellipsis-range.md"))      # [GRC John.3.16-17] with …
def test_missing_section(self): self.assertIn("missing section", msgs("negative/no-conclusion.md"))
def test_contested_without_note_warns(self): self.assertIn("contested", warns("negative/john-1-1-no-note.md"))
def test_sermon_output_template_valid(self): self.assertFalse(errors(Path("templates/sermon-output.md")))
def test_exit_codes(self): ...  # subprocess: positive → 0, negative/misquote.md → 1
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS.
- [ ] **Step 5:** Commit `feat: add sermon validator with fixtures`.

---

### Task 12: SKILL.md and repo docs

**Files:**
- Create: `SKILL.md`, `AGENTS.md`, `README.md`, `LICENSE` (MIT for code; README lists data sources + their licenses, personal non-commercial use), `scripts/lint_skill.py`, `tests/test_skill_lint.py`
- Use `/skill-creator` guidance for SKILL.md description wording (triggers: sermon, preach, prédica, sermón, Greek/Hebrew, original text, exegesis, word study).

**Interfaces:**
- `SKILL.md` frontmatter: `name: original-text-sermons`, `description:` (≤ 1024 chars, includes EN+ES trigger words). Body = spec 7.5 workflow steps 1–10 verbatim in order, hard rules, links to every `references/` and `templates/` file, `lookup.py` command cheat sheet, how to run `install.sh`.
- `lint_skill.py`: checks frontmatter keys, < 500 lines, every relative link resolves, every `scripts/*.py` named in SKILL.md exists. Exit 1 on failure.

- [ ] **Step 1:** Failing test: `test_lint_passes` runs `lint_skill.py`, expects exit 0. Run — FAIL.
- [ ] **Step 2:** Write `lint_skill.py`, `SKILL.md`, `AGENTS.md` (build/test commands, guardrails = spec sections 3–4), `README.md`, `LICENSE`.
- [ ] **Step 3:** Run — PASS.
- [ ] **Step 4:** Commit `feat: add SKILL.md entrypoint and repo docs`.

---

### Task 13: Hooks and install

**Files:**
- Create: `hooks/check-sermon-hook.sh`, `hooks/claude-code.json` (snippet), `hooks/cursor-hooks.json` (snippet), `hooks/pre-commit`, `hooks/README.md`, `install.sh`, `tests/test_hook.py`
- Modify: `SKILL.md` frontmatter (add `hooks:` if the installed Claude Code supports skill-scoped hooks — check `claude --version` and docs via claude-code-guide; otherwise leave frontmatter alone)

**Interfaces:**
- `check-sermon-hook.sh`: reads hook JSON on stdin, extracts `tool_input.file_path` (Claude Code) or `file_path` (Cursor) with `python3 -c`; if path matches `*/sermons/*.md`, runs `check_sermon.py`; on errors writes them to stderr and exits 2 (Claude Code feeds stderr back to the model); otherwise exit 0. Non-sermon paths: exit 0 silently.
- `install.sh [--status|--uninstall]`: build DB if missing (`fetch_sources.sh --check` first) → `ln -sfn <repo> <dir>/original-text-sermons` for each existing dir in `~/.claude/skills ~/.cursor/skills ~/.agents/skills ~/.copilot/skills` → merge hook snippets into `~/.claude/settings.json` (only if not frontmatter-wired) and `~/.cursor/hooks.json` using `python3` json merge, idempotent, backing up the original to `*.bak` first → `git config core.hooksPath hooks` in repo.
- `pre-commit`: `python3 -m unittest discover -s tests` and `check_sermon.py evals/fixtures/positive/*.md`.

- [ ] **Step 1: Failing tests**

```python
def test_hook_blocks_bad_sermon(self):
    r = hook({"tool_input": {"file_path": str(NEG / "misquote.md").replace("negative", "sermons")}})  # copy fixture into tmp/sermons/
    self.assertEqual(r.returncode, 2); self.assertIn("not found", r.stderr)
def test_hook_ignores_other_files(self):
    self.assertEqual(hook({"tool_input": {"file_path": "/tmp/x.py"}}).returncode, 0)
def test_hook_cursor_shape(self):
    self.assertEqual(hook({"file_path": "/tmp/x.py"}).returncode, 0)
```

- [ ] **Step 2:** Run — FAIL. **Step 3:** Implement. **Step 4:** Run — PASS. Then `./install.sh` and `./install.sh --status` — Expected: symlinks listed, hooks wired; running it twice changes nothing.
- [ ] **Step 5:** Commit `feat: add validator hooks and installer`.

---

### Task 14: Evals with skill-creator

**Files:**
- Create: `evals/evals.json`
- Use `/skill-creator` eval workflow to run and grade.

**Interfaces:**
- `evals.json` format (matches sibling repos): `{"skill_name": "original-text-sermons", "evals": [{"id", "prompt", "expected_output", "assertions": [str], "files": []}]}`. The 12 cases of spec 7.9, with these assertions (all evidence-shown, never conclusion):
  1. sermon file passes `check_sermon.py` with 0 errors
  2. Matt 16:18 / Acts 2:38 translation lines use assembly/immerse (or es equivalents); Acts 2:4 no added capitals
  3. John 1:1c, Gal 2:16, Gen 1:26: Greek/Hebrew shown + ≥ 2 options + context note
  4. 1 John 5:7–8, Mark 16:9–20, John 7:53–8:11 reported with their witnesses as late
  5. "dynamis = dynamite" and "aorist = once for all" prompts → corrected with fallacy named
  6. Phil 2:10–11 → MT + LXX Isa 45:21–25 shown, LXX 45:23 τῷ θεῷ noted, no unsupported link
  7. Isa 53:11 → 1QIsaᵃ and LXX readings vs MT shown
  8. non-christian evangelistic sermon → every insider term from `audiences.md` explained on first use
  9. default sections present; example-sermon prompt → its section skeleton reused, none of its sentences copied
  10. same passage es + en both valid
  11. "sermon on grace" → intake questions asked before any drafting
  12. *ekklēsia* study cites `lookup.py usage` counts from LXX + Josephus (+ papyri if present), no claim beyond them

- [ ] **Step 1:** Write `evals.json`.
- [ ] **Step 2:** Run the skill-creator eval loop (with-skill vs baseline) — Expected: every assertion graded; record pass rate in `evals/RESULTS.md`.
- [ ] **Step 3:** Fix SKILL.md/references for failures; re-run until all 12 pass or remaining failures are listed in `RESULTS.md` with reason.
- [ ] **Step 4:** Commit `test: add skill evals and results`.

---

### Task 15: Knowledge graph

- [ ] **Step 1:** Run `/graphify` on the repo root (excluding `sources/` and `data/`).
- [ ] **Step 2:** Check `graphify-out/` exists and the graph shows `SKILL.md → references/*`, `lookup.py → loaders/*`. Add `graphify-out/` to `.gitignore` unless the user wants it committed.
- [ ] **Step 3:** Final: `python3 -m unittest discover -s tests -v`, `python3 scripts/lint_skill.py`, `bash scripts/fetch_sources.sh --check` — all exit 0. Commit `chore: add graphify output config`.
