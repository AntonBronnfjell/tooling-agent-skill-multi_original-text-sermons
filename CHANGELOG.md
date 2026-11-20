# Changelog

All notable changes to this project are documented here, in the style of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.1.0] - 2026-11-19

### Added
- Ground-truth TR and Byzantine verse text: Byzantine from Robinson–Pierpont (2018), TR from eBible grctr verified word-for-word against Scrivener 1894 (unaccented, lower case — TR accents and letter-case are grctr's and unverified). TR verses without ground truth are flagged and the checker warns.
- `order_flags` for edition word order, surfaced by `lookup.py verse` (`order_uncertain`, `order_note`) and `check_sermon.py`, with a final `order_flags_summary` meta row: every THGNT/WH/NA verse whose order is rebuilt from TAGNT marks is flagged (`rebuilt from TAGNT marks` or `order uncertain`; the checker warns); verses checked by hand and found in no printed edition are `known scrambled` per witness (5 TR, 23 THGNT incl. 1 Cor 8:8, 4 WH, 1 NA; the checker errors); KJV verse-break moves and Byz Rom 16:25–27 placement are informational.
- `lookup.py variants` order entries carry a note that they come from TAGNT word data, list `mismatch_with_printed` witnesses and name flagged witnesses (`order_flags`).
- `scripts/check_sblgnt.py`: per-verse cross-check of SBL text against Faithlife SBLGNT, with exact per-chapter verse-boundary shifts and a report of DB-only chapters.
- Validator: EXT editor-bracket notes must sit on the quote's line or in a Notes bullet naming the ref (keywords matched at a word start, so "creditor" does not count); separated lemma lists are allowed, with a long-list warning (slash-separated lists count); an inline-tagged quote ends at non-source punctuation and may open with `…`; Hebrew words joined by maqaf or sof pasuq count as separate words for the untagged-text rule.
- SKILL.md / references: κύριος/θεός casing rule (lower case only as a default, both casings where contested; capitals in the data are never evidence); neutral closings rule with two-way closing examples; handling of word-order warnings.
- Evals 13–15 (iterations 3 and 4 combined: 81/81 assertions, 15/15 cases).

### Changed
- Papyri entries cleaned (Moulton & Milligan still OCR; short cross-reference entries kept); Reina 1569 status recorded as unavailable.
- Edition verse breaks follow the KJV where editions differ (flagged, informational).
- The repeat exemption (a run quoted verbatim on an earlier line counts as tagged) is defined precisely: same words, order and accents; case and punctuation ignored.
- `--lang` help corrected.

### Fixed
- The repeat exemption no longer bridges an elision in the earlier quote.
- List-cap code exemption narrowed to lookup-command snippets.
- Deferred validator, lookup and installer edge cases.

## [1.0.1] - 2026-11-19

### Added
- Google Antigravity install target (`~/.gemini/config/skills`).
- GitHub-flavored README (badges, host table, alerts, collapsible sections).

## [1.0.0] - 2026-11-19

Initial release: an LLM-agnostic skill that writes concise sermons from the Hebrew/Aramaic and Greek text, with a locally built SQLite database of vendored sources, `lookup.py` for text, morphology, usage, variants, comparison and Dead Sea Scrolls, a `check_sermon.py` validator that verifies every original-language quote and the tradition-vocabulary rule, localized templates (Spanish and English fully validated), and install support for Claude Code, Cursor, Copilot and other agents.
