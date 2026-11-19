# Gap-Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the known gaps left after v1 — wrong TR/Byz word order, unverified SBL ending of Romans, loose EXT/lemma validator rules, noisy papyri entries, stale evals — without weakening any fidelity guarantee.

**Architecture:** Replace heuristic TR/Byz reconstruction with vendored ground-truth texts (as SBL already comes from MACULA); keep TAGNT for word data and edition tags; flag anything still uncertain so `lookup.py` and `check_sermon.py` say so. Validator tweaks stay in `scripts/check_sermon.py`; evals re-run and extended.

**Tech Stack:** Python 3 stdlib, unittest, bash; vendored xz sources pinned in `sources/MANIFEST.json`.

**Spec:** `docs/superpowers/specs/2026-11-18-original-text-sermons-design.md`

## Global Constraints

- Python 3 standard library only; tests use `unittest` (`python3 -m unittest discover -s tests`), output pristine.
- Every vendored file: `.xz`, < 100 MB, MANIFEST entry with `upstream`, `commit_or_version`, `sha256`, `license_note`; fixtures mirror paths under `tests/fixtures/sources/`.
- Canonical refs: OSIS `Book.Chapter.Verse`, KJV versification.
- A false accept (wrong text validating) is worse than a false reject; when unsure, flag, never guess.
- No doctrine sources; evals assert evidence/options shown, never conclusions.
- Never run `install.sh` against the real `$HOME` in tests (temp HOME + `OTS_NO_GIT=1`).

## Review Focus

1. A TR/Byz quote of a verse whose order is still unknown (no ground-truth text, TAGNT marks inconsistent) — expected: `check_sermon` WARNs "order uncertain", `lookup` shows `order_uncertain: true`. Test in Task 2.
2. Ground-truth TR/Byz verse numbering that differs from KJV (e.g. 3 John 1:14/15, Rev 12:18/13:1, Rom 16:25–27 placement in Byz) — expected: text lands on the KJV ref. Test in Task 1.
3. A Josephus quote of bracketed text with an unrelated "editor" remark elsewhere in Notes — expected: still WARN/ERROR until the same line or bullet names the EXT ref. Test in Task 4.
4. A word study listing lemmas separated by commas, slashes or "/" — expected: no "untagged run" error; two unseparated words still error. Test in Task 4.
5. Re-running evals against the stricter validator — expected: newly written sermons pass with inline tags; historical runs stay archived, not edited. Test in Task 6.

---

### Task 1: Vendor ground-truth TR and Byzantine texts

**Files:**
- Modify: `sources/MANIFEST.json`, `scripts/fetch_sources.sh` (only if a new download shape is needed)
- Create: `sources/tr/*.xz`, `sources/byz/*.xz`, `tests/fixtures/sources/tr/*.xz`, `tests/fixtures/sources/byz/*.xz`
- Create: `scripts/loaders/greek_editions.py`; Modify: `scripts/build_db.py` (loader order: after `macula`)
- Test: `tests/test_greek_editions.py`

**Interfaces:**
- Consumes: `refs.parse_ref/to_osis`, `norm.display/match_key`, TAGNT word rows (witness `TAGNT`, `editions` tokens).
- Produces: `greek_editions.load(conn, sources_dir) -> int`; replaces `verses` rows for corpus `grnt` witnesses `TR` and `Byz`; records `meta('tr_source', …)`, `meta('byz_source', …)`; a table `order_flags(corpus TEXT, witness TEXT, ref TEXT, reason TEXT)` (add to `db.SCHEMA`) listing verses whose text could not be taken from ground truth.

- [ ] **Step 1:** Choose sources (verify they exist, are public domain, and carry accents): Byzantine — `byztxt/byzantine-majority-text` (Robinson–Pierpont); TR — Scrivener 1894 (`byztxt/greektext-scrivener` or eBible `grctr`). Pin in MANIFEST; if no accented machine-readable TR exists, record `status: deferred` with the reason and skip TR (Task 2 then flags all reordered TR verses).
- [ ] **Step 2:** Cut fixtures with real rows for 1Tim.1.1, Acts.20.28, Mark.7.30, 2Pet.1.18, Luke.15.30, 3John.1.14–15, Rom.16.24–27.
- [ ] **Step 3: Failing tests**

```python
def test_tr_1tim_1_1(self): self.assertIn("Ἰησοῦ Χριστοῦ", text("TR", "1Tim.1.1"))
def test_tr_byz_acts_20_28(self):
    for w in ("TR", "Byz"): self.assertIn("τοῦ ἰδίου αἵματος", text(w, "Acts.20.28"))
def test_mark_7_30_not_scrambled(self): self.assertNotIn("τὴν τὸ", text("TR", "Mark.7.30"))
def test_kjv_refs(self):  # source numbering mapped to KJV refs
    self.assertTrue(text("Byz", "3John.1.14")); self.assertIsNone(text_or_none("Byz", "3John.1.15"))
```

- [ ] **Step 4:** Implement: parse source → per-verse text → map source refs to KJV refs (reuse the word-alignment approach in `loaders/macula.py` `_assign_refs` against TAGNT words of that edition when numbering differs) → replace `verses` rows; verses with no ground-truth row keep the reordered TAGNT text and get an `order_flags` row (`reason='no ground truth'`).
- [ ] **Step 5:** Run tests; full build `python3 scripts/build_db.py`; report how many TR/Byz verses changed vs the reordered TAGNT text and list any non-trivial diffs (≥3 words).
- [ ] **Step 6:** Commit `feat: TR and Byzantine verse text from ground-truth editions`.

---

### Task 2: Flag uncertain word order

**Files:**
- Modify: `scripts/loaders/stepbible.py` (emit `order_flags` for the at-risk class), `scripts/lookup.py`, `scripts/check_sermon.py`
- Test: `tests/test_order_flags.py`

**Interfaces:**
- Consumes: `order_flags` (Task 1).
- Produces: `lookup.py verse` JSON field `order_uncertain: bool` (+ `order_note`); `check_sermon` WARN `order uncertain for <WITNESS> <ref>: verify against a printed edition`.

- [ ] **Step 1: Failing tests** — a fixture verse flagged for THGNT (or TR if Task 1 deferred TR) → `verse` shows `order_uncertain: true`; a sermon quoting it → WARN containing `order uncertain`; an unflagged verse → no field / no WARN.
- [ ] **Step 2:** In `stepbible.py`, flag a reordered verse when a moved word's span contains a word not printed by every edition, or the verse contains `διαπαντός`; do not reorder inside those spans (`# ponytail:` comment naming the ceiling).
- [ ] **Step 3:** Run tests + full build; print flag counts per witness.
- [ ] **Step 4:** Commit `feat: flag and surface uncertain edition word order`.

---

### Task 3: Verify SBL text against the published SBLGNT

**Files:**
- Modify: `sources/MANIFEST.json`; Create: `sources/sblgnt/*.xz` (Faithlife `SBLGNT` repo, CC BY 4.0), fixture excerpt
- Create: `scripts/check_sblgnt.py`; Test: `tests/test_check_sblgnt.py`

**Interfaces:**
- Produces: `check_sblgnt.py` (maintenance script like `check_lxx_alignment.py`): compares `verses` SBL rows with the Faithlife text per KJV ref, prints mismatches; exit 1 if any mismatch beyond punctuation/case.

- [ ] **Step 1:** Vendor Faithlife SBLGNT text; fixture with Rom.16.23–27.
- [ ] **Step 2: Failing test** — on the fixture DB, `check_sblgnt` reports Rom.16.25–27 status exactly as the Faithlife text shows (present or absent); no claim beyond the file.
- [ ] **Step 3:** Implement; run on the real DB; if MACULA disagrees with Faithlife (e.g. Rom 16:25–27), make Faithlife authoritative for those verses in `loaders/macula.py` and record the diff list in the report.
- [ ] **Step 4:** Update README "Known limitations" accordingly. Commit `feat: cross-check SBL text against Faithlife SBLGNT`.

---

### Task 4: Tighten EXT-bracket and lemma-list validator rules

**Files:**
- Modify: `scripts/check_sermon.py` (EDITOR_NOTE check; `inline_quotes` run splitting)
- Test: `tests/test_check_sermon.py`

- [ ] **Step 1: Failing tests**

```python
def test_ext_bracket_note_must_name_ref(self):  # "editors enclose [[ ]]" about Mark 16 elsewhere in Notes
    self.assertIn("bracketed", errors_or_warns("ext-bracket-unrelated-note.md"))
def test_ext_bracket_note_same_line_ok(self):    # Notes bullet: "Ant.18.63 — editor-bracketed in Niese"
    self.assertFalse(errors("ext-bracket-named.md"))
def test_lemma_list_allowed(self):               # "Related lemmas: βάπτισμα, βαπτισμός / βαπτισμοῦ"
    self.assertFalse(errors("lemma-list.md"))
def test_two_adjacent_words_still_error(self):   # "καὶ θεὸς" untagged
    self.assertIn("untagged", msgs("two-words-untagged.md"))
```

- [ ] **Step 2:** Implement: the bracket note counts only on the same line/bullet as the EXT ref or a line naming that ref; runs split on `,`, `;`, `/`, `·` (each piece judged alone).
- [ ] **Step 3:** Run tests; all positives + template still 0 errors. Commit `fix: scope EXT bracket notes; allow separated lemma lists`.

---

### Task 5: Clean papyri entries and retry Reina 1569

**Files:**
- Modify: `scripts/loaders/ext.py` (papyri), `scripts/lookup.py` (`usage` papyri output), `sources/MANIFEST.json` (Reina 1569 entry)
- Test: `tests/test_ext.py`

- [ ] **Step 1: Failing tests** — entries with body < 20 chars or headword ≤ 2 chars are dropped; duplicate lemmas merged into one entry (bodies joined with `\n---\n`); `usage` returns at most one papyri entry per lemma.
- [ ] **Step 2:** Implement; full build; report entry count before/after.
- [ ] **Step 3:** Search once more for a machine-readable Reina 1569 (archive.org text, GitHub, Wikisource). If found and usable: vendor + translation loader picks it up (lang es). If not: set MANIFEST reason with the date searched; no code.
- [ ] **Step 4:** Commit `fix: cleaner papyri entries; Reina 1569 status`.

---

### Task 6: Re-run and extend evals

**Files:**
- Modify: `evals/evals.json` (+3 cases), `evals/RESULTS.md`
- Create: `evals/runs/iteration-3/**`

- [ ] **Step 1:** Add evals: (13) TR quote of Acts 20:28 and 1 Tim 1:1 — assertions: TR text matches lookup, Notes show each edition's order, no verdict; (14) word study whose Notes cite variant readings — every original-language phrase inline-tagged and validating; (15) Antigravity-style chat answer in Spanish — `--quotes-only` used, quotes valid.
- [ ] **Step 2:** Run all 15 evals (runner subagents, with-skill) into `evals/runs/iteration-3/`; grade with `evals/grade_programmatic.py` + grader; append "Iteration 3" to `RESULTS.md` with pass rate. Historical iteration-1/2 runs stay untouched.
- [ ] **Step 3:** Fix SKILL.md/references for any failure (one fix round), re-run failing evals only.
- [ ] **Step 4:** Commit `test: eval iteration 3`.

---

### Task 7: Small deferred fixes

**Files:** `scripts/otslib/references.py`, `scripts/check_sermon.py`, `scripts/lookup.py`, `install.sh`, tests per file.

- [ ] **Step 1: Failing tests, one each:** `#` inside a custom section name is kept (comment stripping only for `language`); BOM before `---` is stripped; `lookup` unknown-witness message lists witnesses that have the ref; `install.sh --uninstall` removes an empty `{"version":1}` Cursor hooks file it created; old unquoted Cursor entry is migrated on install.
- [ ] **Step 2:** Implement each; run full suite + lint. Commit `fix: deferred validator, lookup and installer edge cases`.

---

### Task 8: Re-graph and release notes

- [ ] **Step 1:** `graphify` `--update` on the repo (same excludes); check health warnings.
- [ ] **Step 2:** README: update test badge count, "Known limitations"; add a CHANGELOG entry. Commit `docs: v1.1 notes`.
