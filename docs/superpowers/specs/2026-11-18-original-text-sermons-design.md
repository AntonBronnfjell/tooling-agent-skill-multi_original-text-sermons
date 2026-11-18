# Design: `original-text-sermons` skill

- **Repo:** `tooling-agent-skill-multi_original-text-sermons` (validated against repo-name-conventions)
- **Skill name:** `original-text-sermons`
- **Location:** `~/Development/anton.social/tooling-agent-skill-multi_original-text-sermons/`
- **Date:** 2026-11-18 · **Status:** draft for approval

## 1. Intent

Build concise, preachable sermons straight from the Hebrew/Aramaic and Greek texts, translated fresh and naturally into whatever language is requested — instead of leaning on modern published translations that carry later doctrine and church tradition in their wording.

"Non-institutional" means **no doctrine, no tradition**: the target is the text as close to the 1st century as surviving evidence allows. The skill's only loyalty is fidelity to the text. It holds no doctrinal position of its own.

Single user, personal, non-commercial use. Licenses are not a constraint.

## 2. Goals

1. Every original-language quote in a sermon is pulled from local data, never from model memory, and is mechanically verified.
2. Translation in two layers: literal word-for-word (with glosses), then natural in the target language.
3. Where the text honestly allows more than one reading, show the original, each option, and which one context favors. Never pick silently.
4. Linguistic rigor: Greek and Hebrew grammar checks, exegetical-fallacy checks, LXX usage as the lexicon of NT Greek, 1st-century usage over later meaning.
5. Translation comparison: for key verses, show how several published translations render it and flag where they diverge from the original (added words, harmonization, capitalization, tradition vocabulary, late textual readings).
6. Text-critical awareness: show where early witnesses differ from late ones (e.g. TR vs early text) for the passage.
7. Audience- and specialization-aware output, following a sermon template (default or extracted from a user example).
8. Works in Claude Code, Cursor, Copilot (portable SKILL.md + Python scripts).

## 3. Non-goals

- No doctrinal position, creeds, church fathers, denominational statements, systematic theology frameworks, or commentaries as sources.
- No full Bible translation; only passages a sermon uses.
- No TBI-style scoring, no web app, no MCP server (possible later on top of the same DB).
- No hosting/publishing of sermons.

## 4. Anti-goals (failure even if it "works")

- A sermon that quotes Greek/Hebrew the data does not contain.
- A translation line using later church vocabulary where the text has a plain word (e.g. "church" for *ekklēsia*, "baptize" for *baptizō*) without showing the plain meaning.
- Silently resolving a contested reading (e.g. John 1:1c, *pistis Christou*, Elohim plurality, Acts 2:38, 1 John 5:7) in either direction.
- Word-study preaching fallacies: root fallacy, illegitimate totality transfer, anachronism ("dynamis = dynamite").
- Long sermons. "Concise" = ~1–2 pages, ~15–20 minutes spoken.

## 5. Constraints

- Python 3 standard library only (`sqlite3`, `csv`, `xml.etree`, `unicodedata`, `json`, `gzip`/`lzma`). No pip installs.
- Repo root is the skill root (SKILL.md at root), matching sibling skills in `anton.social/`.
- Install by **symlinking** the repo into each agent's skills dir (same pattern as `centralized-file-component`), so there is one copy on disk.
- SKILL.md < 500 lines; detail lives in `references/`.

## 6. Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | Raw source data vendored in the repo, scripts parse it directly | Offline and self-contained; but slow re-parsing of mixed formats |
| B | Small skill, data downloaded once, built into one SQLite DB | Fast exact lookups; depends on upstream availability at fetch time |
| C | Local MCP server over the same DB | Clean tool calls; extra process + config per agent, more code |

**Picked: A + B.** Raw sources are vendored (compressed) in the repo — offline, permanent, pinned, survives upstream disappearing. `build_db.py` builds one SQLite DB from those vendored files, no network. Symlink install means one copy on disk regardless of agent count. C rejected: no fidelity gain for one user; can be added later over the same DB.

## 7. Design

### 7.1 Repo layout

```
tooling-agent-skill-multi_original-text-sermons/
├── SKILL.md                      # entrypoint workflow + hard rules
├── AGENTS.md  README.md  LICENSE
├── references/
│   ├── fidelity-rules.md         # quoting, two-layer translation, contested readings
│   ├── linguistics-greek.md      # aspect, voice, article, genitives, conditionals, Semitisms
│   ├── linguistics-hebrew.md     # wayyiqtol, aspect, construct chains, parallelism, idioms, divine names
│   ├── exegetical-fallacies.md   # root, totality transfer, anachronism, word-concept, etc.
│   ├── translation-comparison.md # how to compare versions and classify divergences
│   ├── text-criticism.md         # early vs late witnesses, how to report variants
│   ├── tradition-vocabulary.md   # per language: tradition term -> plain rendering(s)
│   ├── specializations.md        # theology, apologetics, evangelistic, teaching, pastoral
│   └── audiences.md              # christian, non-christian, mixed
├── templates/
│   ├── big-idea.md               # default: expository Big Idea, 3 points
│   ├── hook-book-look-took.md    # preset, suits evangelistic / non-christian
│   └── sermon-output.md          # file format the validator expects
├── sources/                      # vendored raw data, compressed, pinned (see 7.2)
│   ├── MANIFEST.json             # source -> upstream URL, commit/version, sha256, license note
│   └── user/                     # drop-in CSVs for extra translations (RVR1960, NVI...) — gitignored
├── data/bible.db                 # built, gitignored
├── scripts/
│   ├── fetch_sources.sh          # refresh vendored files at pinned versions (maintenance only)
│   ├── build_db.py               # sources/ -> data/bible.db
│   ├── lookup.py                 # query CLI (see 7.4)
│   └── check_sermon.py           # validator used by hooks, skill, evals
├── hooks/                        # host hook wiring (see 7.8)
├── evals/evals.json  evals/fixtures/
├── tests/                        # unittest for scripts
└── install.sh                    # symlink into agent dirs + build DB
```

### 7.2 Sources (vendored)

| Source | Gives | Role |
|---|---|---|
| STEPBible TAHOT | Hebrew/Aramaic OT (Leningrad), morphology, Ketiv/Qere, glosses | OT base text |
| STEPBible TAGNT | Greek NT words with edition markers (NA, SBL, THGNT, WH, Byz, TR) | NT base text + automatic early-vs-late variant reporting |
| STEPBible TBESH / TBESG | Brief Hebrew / Greek lexicons | Glosses, lexical range |
| STEPBible TVTMS | Versification mappings | Align refs across Hebrew, LXX, English, Spanish numbering |
| MACULA Greek + Hebrew (Clear Bible) | Syntax trees, clause roles, Louw-Nida / SDBH semantic domains | Linguistic analysis, semantic range |
| LXX tagged (CATSS/Rahlfs; Swete text as fallback) | Greek OT with morphology | 1st-century Greek OT; "LXX as NT lexicon" lookups |
| ETCBC DSS (biblical scrolls only) | Dead Sea Scrolls biblical manuscripts, morphology, per-manuscript (1QIsaᵃ, 4QSamᵃ…) | 1st-century Hebrew witness where extant |
| Josephus, Philo — Greek texts (Perseus canonical-greekLit / First1KGreek TEI) | 1st-century Jewish Greek prose | Word usage evidence and historical background only — never doctrine or interpretation (Philo's allegory is not a source) |
| Moulton & Milligan, *Vocabulary of the Greek Testament* (public domain) | NT words as used in papyri and inscriptions | Everyday 1st-century usage per lemma |
| Comparison translations (public domain) | EN: KJV, YLT, BSB, WEB · ES: RV1909, Reina 1569 (if obtainable) | Translation-comparison step |
| `sources/user/*.csv` | Any translation the user supplies (`ref,text` with a header naming the version) | Compare against modern translations user owns |

Not used: creeds, commentaries, study-Bible notes, unfoldingWord notes (tradition leak risk).

### 7.3 Database (sketch; builder may refine)

- `words(corpus, ref, pos, surface, lemma, strongs, morph, gloss, editions, domain, syntax_role)` — corpus ∈ {hebot, grnt, lxx, dss, ext}; `ext` lemmatization may be partial — store what the source provides
- `papyri_vocab(lemma, entry)` — Moulton & Milligan entry text per lemma
- `verses(corpus, witness, ref, text)` — normalized surface text (NFC) per verse **per witness**: NT witnesses = TAGNT editions (`SBL` default, `NA`, `THGNT`, `WH`, `Byz`, `TR`); DSS witness = manuscript siglum (`1QIsaa`…); HEB witness = `WLC` (+ `Qere`); LXX = `Rahlfs`/`Swete`
- `translations(version, lang, ref, text)`
- `lexicon(lemma, strongs, lang, gloss, definition)`
- `versification(scheme, ref, canonical_ref)`
- `variants(ref, pos, reading, editions)` — derived from TAGNT edition markers and Ketiv/Qere

Canonical ref format: OSIS-like `Book.Chapter.Verse` (e.g. `John.1.1`), English book abbreviations, input accepts Spanish names too (`Juan 1:1`).

### 7.4 `lookup.py` commands

- `verse <ref> [--corpus]` — original text + per-word morphology + glosses
- `interlinear <ref>` — literal layer source
- `variants <ref>` — readings by edition, labeled early/critical vs late/TR/Byz
- `word <lemma|strongs>` — lexicon, semantic domain, NT usage counts, LXX usage (which Hebrew words it renders)
- `compare <ref> [--versions ...]` — published translations side by side
- `dss <ref>` — DSS reading where extant, diff vs Masoretic
- `lxx <ref>` — LXX reading, diff vs Masoretic
- `search <lemma> [--corpus]` — occurrences
- `usage <lemma>` — 1st-century usage report: counts + sample contexts across NT, LXX, Josephus, Philo, plus the Moulton & Milligan entry
- All output JSON by default, `--format text` for humans.

### 7.5 Skill workflow (SKILL.md)

1. **Intake** — ask only what's missing, one short message:
   topic or passage · specialization (theology, apologetics, evangelistic, teaching/discipleship, pastoral) · audience (christian, non-christian, mixed) · output language · template ("use default template, or paste an example sermon whose structure I should copy?").
2. **Passage** — if only a topic is given, propose 1–3 passages and let the user choose.
3. **Text** — `lookup.py verse/variants/dss/lxx` for the passage. Never quote from memory.
4. **Linguistics** — apply the Greek or Hebrew reference checks and fallacy checks to key words/clauses; `lookup.py word` for key lemmas incl. LXX usage.
5. **Comparison** — `lookup.py compare` on key verses; classify divergences per `translation-comparison.md`.
6. **Translate** — literal layer, then natural layer in target language, per `fidelity-rules.md` and `tradition-vocabulary.md`.
7. **Structure** — fill the chosen template; if an example was supplied, extract only its skeleton (sections, order, relative length) — discard its wording and theology.
8. **Adapt** — specialization shapes content; audience shapes vocabulary, illustrations, and the response/call.
9. **Write** — save to `./sermons/YYYY-MM-DD-<slug>.<lang>.md` in the current working directory, in the `sermon-output.md` format; also show it in chat.
10. **Verify** — run `check_sermon.py` on the file; fix every error before presenting.

Usage claims (occurrence counts, "LXX renders Hebrew X with Y", semantic domain) must come from `lookup.py` output in the same session, never memory. Not machine-checked in prose; enforced by SKILL.md rule and eval assertions.

### 7.6 Sermon output format (validator contract)

- YAML frontmatter: `passage, language, specialization, audience, template, date`.
- Template sections as `##` headings (names defined per template file).
- Every original-language quote as a parseable block:

```
> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος
> Literal: and God was the word
> Natural: …
```

  Tag grammar: `[CORPUS[:WITNESS] Ref]`. Corpus: `HEB`, `ARC`, `GRC` (NT), `LXX`, `DSS`, `EXT` (Josephus/Philo; witness = author, ref = work citation, e.g. `[EXT:Josephus Ant.18.63]`). Witness optional, defaults: `GRC`→`SBL`, `HEB`/`ARC`→`WLC`, `LXX`→`Rahlfs`. `DSS` and `EXT` require a witness (`[DSS:1QIsaa Isa.53.11]`). A late reading must name its witness (`[GRC:TR 1John.5.7]`), so a TR-only text can never pass as a plain `[GRC …]` quote.
- "Notes" section at end: variants, contested readings with options, translation-comparison findings.

### 7.7 `check_sermon.py` (validator)

Errors (exit 1):
- Quoted original text is not a contiguous match in `verses` for that corpus+witness+ref (NFC-normalized; `…` allowed to elide).
- Unknown ref, corpus tag, or witness; `DSS` quote without witness.
- Missing frontmatter keys or required template sections.
- A `Literal:`/`Natural:` line missing after a quote.
- A `Literal:`/`Natural:` line contains a term listed in `tradition-vocabulary.md` for that language (case-insensitive whole-word match). Always an error on those two lines — the plain rendering goes in the line, the tradition term may be discussed in prose or Notes. Prose is not checked.

Capitalization is **not** checked mechanically (it would force a side on contested readings). Rule lives in `fidelity-rules.md`: no capitals added to *pneuma hagion*; θεός/אֱלֹהִים rendered "God" only where target-language grammar treats it as a name, and contested places (John 1:1c, Gen 1:26) show the options instead.

Warnings (exit 0):
- Spoken-length estimate outside ~15–20 min (word count based).
- Contested-reading refs (list in `fidelity-rules.md`) quoted without an options note.

### 7.8 Hooks

- **Claude Code:** `PostToolUse` on `Write|Edit` for `sermons/*.md` runs `check_sermon.py`; failure output goes back to the model. Wired via skill frontmatter hooks if supported by the installed version, else `install.sh` merges into `~/.claude/settings.json`.
- **Cursor:** `afterFileEdit` entry in `~/.cursor/hooks.json` with same command.
- **Copilot:** no hook; SKILL.md step 10 covers it.
- **Repo dev:** `pre-commit` runs `tests/` and `check_sermon.py` on `evals/fixtures/positive/`.

### 7.9 Evals

`evals/evals.json` (skill-creator format: `prompt`, `expected_output`, assertions) covering the cases below. **Assertions check that evidence and options were shown, never that a particular conclusion was reached.**
1. Quote fidelity — every quote passes `check_sermon.py`.
2. Tradition traps — Matt 16:18 (*ekklēsia*), Acts 2:38 (*baptizō*): plain rendering on translation lines; Acts 2:4 (*pneuma hagion*): no added capitals.
3. Contested readings shown, not resolved — John 1:1c, Gal 2:16 (*pistis Christou*), Gen 1:26 (Elohim/"us").
4. Text criticism — 1 John 5:7–8 (Comma), Mark 16:9–20, John 7:53–8:11 reported as late.
5. Fallacies — prompt baiting "dynamis = dynamite" and aorist "once for all" must be refused/corrected.
6. LXX usage — Phil 2:10–11 alludes to Isa 45:23: skill shows MT and LXX of Isa 45:21–25 (note LXX 45:23 reads τῷ θεῷ, κύριος/YHWH sits in vv. 21, 24–25) and makes no link the data doesn't show.
7. DSS — Isa 53:11 "light" (1QIsaᵃ/LXX vs MT).
8. Audience — non-christian evangelistic sermon contains no unexplained insider terms.
9. Template — default sections present; example-sermon extraction copies structure, not wording.
10. Languages — same passage in ES and EN, both valid.
11. Intake — bare "sermon on grace" triggers the intake questions.
12. 1st-century usage — *ekklēsia* word study cites `lookup.py usage` evidence (LXX, Josephus, papyri) and draws no conclusion beyond it.

Plus `evals/fixtures/{positive,negative}/` sermons for the validator, and `tests/` unit tests for `lookup.py`, `build_db.py`, `check_sermon.py`.

### 7.10 Install

`install.sh`: build `data/bible.db` if missing → symlink repo into `~/.claude/skills/original-text-sermons`, `~/.cursor/skills/…`, `~/.agents/skills/…`, `~/.copilot/skills/…` (only for dirs that exist) → wire hooks (7.8). `--status` and `--uninstall` flags.

## 8. Left to the builder

- Exact upstream repo/commit for each source; record in `MANIFEST.json`.
- Compression format and whether any file needs Git LFS (keep each file < 100 MB; repo target < 500 MB).
- Exact DB schema/indexes; Hebrew/Greek normalization details (accents, final forms, maqaf) for matching.
- Contents of `tradition-vocabulary.md` (start with ~20 terms per language EN/ES) and the contested-readings list.
- Template section names.
- Reina 1569 availability; drop if not obtainable as text.
- Source for a machine-readable Moulton & Milligan text (OCR quality varies); if only scans exist, defer it and keep `usage` working on the other corpora.

## 9. Calls made by Claude (not explicitly decided by the user — check these)

- Skill name `original-text-sermons`; repo layout mirrors sibling skills (repo root = skill root, symlink install).
- Default NT witness = SBL; default OT = WLC; default LXX = Rahlfs.
- Non-biblical Dead Sea Scrolls excluded.
- unfoldingWord notes, MCP servers excluded.
- "Concise" = ~1–2 pages, ~15–20 min.
- Sermons saved to `./sermons/` in the current directory and shown in chat.
- Capitalization rule (no added capitals on *pneuma hagion*; "God" as name only where grammar requires; contested places show options) — enforced by rules, not the validator.
- Tradition terms are always errors on translation lines, free in prose.
- Evals assert evidence/options shown, never conclusions.
- Python stdlib only; Copilot gets no hook.
