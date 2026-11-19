# AGENTS.md — original-text-sermons

This repository **is** the `original-text-sermons` agent skill (repo root = skill root). It writes concise sermons from the Hebrew/Aramaic and Greek texts, with every original-language quote pulled from a local SQLite database and mechanically verified. Read [SKILL.md](SKILL.md) for the runtime workflow; this file is for contributors and coding agents working on the repo.

## Commands

Run from the repo root. Python 3 standard library only — never `pip install` anything.

```bash
python3 scripts/build_db.py                       # sources/ -> data/bible.db (offline; --db PATH; --only <loader> needs --db)
python3 -m unittest discover -s tests -v          # full test suite (unittest only)
python3 scripts/lint_skill.py                     # SKILL.md frontmatter, < 500 lines, links, named scripts
python3 scripts/check_sermon.py evals/fixtures/positive/*.md   # validator must pass every positive fixture
python3 scripts/check_sermon.py evals/fixtures/negative/<f>.md # ...and flag each negative one (ERROR, or WARN-only for john-1-1-no-note / stitched-single-words)
python3 scripts/lookup.py --format text verse John.1.1          # smoke-test the DB
bash scripts/fetch_sources.sh --check             # verify sha256 of vendored sources (no network)
python3 scripts/check_lxx_alignment.py            # LXX -> KJV versification sanity check (real data)
```

`install.sh` (repo root) builds the DB if missing and symlinks the repo into each agent's skills directory (Claude Code, Cursor, Copilot, `~/.agents`, and Google Antigravity at `~/.gemini/config/skills`); it supports `--status` and `--uninstall`.

Exit codes: `lookup.py` 1 = unknown ref/witness, 2 = DB missing; `check_sermon.py` 1 = errors, 2 = DB missing; `lint_skill.py` 1 = lint failure.

## Repo map

| path | role |
|---|---|
| `SKILL.md` | runtime entrypoint: 10-step workflow, hard rules, `lookup.py` cheat sheet (< 500 lines) |
| `references/` | rules the model loads on demand: fidelity, Greek/Hebrew linguistics, fallacies, comparison, text criticism, tradition vocabulary, contested readings, specializations, audiences |
| `templates/` | sermon templates (`sections:` + `sections_es:` frontmatter) and `sermon-output.md`, a complete example that validates |
| `scripts/lookup.py` | query CLI: `verse interlinear variants word usage compare dss lxx search` |
| `scripts/check_sermon.py` | validator: quotes vs DB, tags, refs, frontmatter, sections, tradition vocabulary on translation lines |
| `scripts/build_db.py`, `scripts/loaders/` | builds `data/bible.db` from `sources/` |
| `scripts/otslib/` | shared code: DB path, normalization, refs/versification, reference-table parsing |
| `scripts/fetch_sources.sh` | maintenance: refresh vendored sources at pinned versions, or `--check` hashes |
| `scripts/check_lxx_alignment.py` | maintenance: LXX versification check |
| `scripts/lint_skill.py` | lints `SKILL.md` |
| `sources/` | vendored raw data, xz-compressed, each file < 100 MB; `MANIFEST.json` lists upstream, commit/version, sha256, license note |
| `sources/user/` | user CSV translations (gitignored except README) |
| `data/bible.db` | built DB (gitignored); `$OTS_DB` overrides the path |
| `evals/` | validator fixtures (`fixtures/positive/`, `fixtures/negative/`) and the skill evals (`evals.json`, skill-creator format) |
| `tests/` | `unittest` suites for every script (synthetic fixtures under `tests/fixtures/`) |
| `docs/superpowers/specs/` | design spec (authoritative intent, goals, anti-goals) |

## Guardrails

These come from the design spec (§3 non-goals, §4 anti-goals) and apply to code, references, templates, fixtures and evals alike.

**Non-goals — never add:**

- a doctrinal position, creeds, church fathers as interpreters, denominational statements, systematic-theology frameworks, commentaries, study-Bible notes or unfoldingWord notes as sources (a church father may appear only as a dated text-critical witness);
- full Bible translation (only passages a sermon uses), TBI-style scoring, a web app, an MCP server, or sermon hosting/publishing;
- third-party Python packages.

**Anti-goals — a change that does any of these is a failure even if tests pass:**

- a sermon, reference or fixture that quotes Greek/Hebrew the data does not contain (copy every form from `lookup.py` output; never type it from memory);
- a translation line using later church vocabulary where the text has a plain word (*church* for ἐκκλησία, *baptize* for βαπτίζω) without showing the plain meaning;
- silently resolving a contested reading (John 1:1c, *pistis Christou*, Elohim plurality, Acts 2:38, 1 John 5:7…) in either direction;
- word-study fallacies: root fallacy, illegitimate totality transfer, anachronism ("dynamis = dynamite");
- long sermons: concise = ~500–1300 words of body, ~15–20 minutes spoken.

**Evals and fixtures assert that evidence and options were shown — never that a particular doctrinal conclusion was reached.**

## Conventions

- Canonical refs: OSIS `Book.Chapter.Verse`, KJV versification; single-chapter ranges only (`John.3.16-17`).
- Quote tags: `[CORPUS[:WITNESS] Ref]`; corpora `HEB ARC GRC LXX DSS EXT`; defaults GRC→SBL, HEB/ARC→WLC, LXX→Rahlfs; DSS and EXT require a witness. DB corpus keys: `hebot grnt lxx dss ext`.
- Machine-read tables: the `term` column of `references/tradition-vocabulary.md`, the `ref` column of `references/contested-readings.md`, and `sections:`/`sections_es:` in template frontmatter are parsed by `scripts/otslib/references.py` — keep their format.
- Keep `SKILL.md` under 500 lines; put detail in `references/`. Every relative link in `SKILL.md` must resolve and every `scripts/*` it names must exist (`lint_skill.py`).
- New sources: vendor compressed under `sources/`, add a `MANIFEST.json` entry with `upstream`, `commit_or_version`, `sha256`, `license_note`.
- Tests first (`unittest`), then code. Commit messages end with the `Co-Authored-By` trailer when an agent wrote the change.
