# Changelog

All notable changes to this project are documented here, in the style of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-11-19

### Added
- Ground-truth TR and Byzantine verse text: Byzantine from Robinson–Pierpont (2018), TR from eBible grctr verified word-for-word against Scrivener 1894 (unaccented). TR verses without ground truth are flagged and the checker warns; 5 known-scrambled TR verses are rejected.
- Order flags for uncertain edition word order, surfaced in lookup output, with a final `order_flags_summary` meta row.
- `scripts/check_sblgnt.py`: per-verse cross-check of SBL text against Faithlife SBLGNT, with an explicit stream allowlist and a report of DB-only chapters.
- Validator rules: EXT bracket-note scope; separated lemma lists and a long-list cap (slash-separated lists count); inline-tag boundary at non-source punctuation and a permitted leading ellipsis; repeat exemption for verbatim repeats of earlier quotes; κύριος/θεός casing rule (lower case only as a default, both casings where contested); neutral closings rule with two-way closing examples.
- Evals 13–15 (iterations 3 and 4: 81/81 assertions, 15/15 cases).
- Google Antigravity install target and a GitHub-flavored README.

### Changed
- Papyri entries cleaned (Moulton & Milligan still OCR; short cross-reference entries kept); Reina 1569 status recorded as unavailable.
- Chapter allowlist replaced with exact per-chapter verse shifts.
- Edition verse breaks follow the KJV where editions differ (flagged, informational).
- `--lang` help corrected.

### Fixed
- Repeat exemption no longer bridges an elision in the earlier quote.
- List-cap code exemption narrowed.
- Deferred validator, lookup and installer edge cases.
- Eval 13 assertions.

## [1.0.0] - 2026-11-19

Initial release: an LLM-agnostic skill that writes concise sermons from the Hebrew/Aramaic and Greek text, with a locally built SQLite database of vendored sources, `lookup.py` for text, morphology, usage, variants, comparison and Dead Sea Scrolls, a `check_sermon.py` validator that verifies every original-language quote and the tradition-vocabulary rule, localized templates (Spanish and English fully validated), and install support for Claude Code, Cursor, Copilot and other agents.
