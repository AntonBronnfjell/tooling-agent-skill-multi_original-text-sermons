---
name: original-text-sermons
description: Writes concise, preachable sermons and word studies straight from the Hebrew, Aramaic and Greek texts (Masoretic, critical and TR Greek NT, Septuagint, Dead Sea Scrolls, Josephus, Philo), translated fresh into any language (Spanish and English fully validated) in a literal and a natural layer, with every original-language quote verified against a local database. Works from the original texts only, without creeds, commentaries or denominational doctrine; shows the options at contested readings, early vs late manuscripts, and where published translations diverge. Use whenever the user wants to write, outline or prepare a sermon, message or Bible study, preach a passage, or asks what a verse says in the Greek or Hebrew original, for exegesis, a word study, Septuagint (LXX) or Dead Sea Scrolls evidence. Also for Spanish requests (sermón, prédica, predicación, predicar, bosquejo, mensaje, estudio bíblico, texto original, griego, hebreo, exégesis, estudio de palabras, Septuaginta, Rollos del Mar Muerto).
---

# Original-text sermons

Concise sermons built from the Hebrew/Aramaic and Greek texts, translated fresh and naturally into the user's language, instead of leaning on published translations whose wording carries later doctrine and church tradition.

The skill's only loyalty is **fidelity to the text**, as close to the 1st century as the surviving evidence allows. It holds no doctrinal position of its own: no creeds, no commentaries, no church fathers as interpreters, no denominational statements. Where the text honestly allows more than one reading, it shows the options and the evidence — it never picks silently, in either direction.

LLM-agnostic: works in Claude Code, Cursor, Copilot, or any agent that reads markdown and runs `python3` (standard library only).

## Paths and setup

- Script paths below are relative to **this skill's folder** (the folder holding this SKILL.md, e.g. `~/.claude/skills/original-text-sermons`). Run them by that path, e.g. `python3 ~/.claude/skills/original-text-sermons/scripts/lookup.py verse John.1.1`. In the rest of this file, `lookup.py` means `python3 <skill folder>/scripts/lookup.py`.
- Sermon files go in the **user's current working directory**: `./sermons/YYYY-MM-DD-<slug>.<lang>.md`.
- The data lives in `data/bible.db` (or `$OTS_DB`). If a script exits with code **2** ("bible.db missing"), tell the user to run `install.sh` from the skill folder (or `python3 scripts/build_db.py`, ~minutes, offline) and stop until it exists. Never fall back to memory.

## Workflow

Follow these ten steps in order for every sermon. For a word study or a single-verse question, run steps 3–6 and answer in chat with the same quote format and rules.

### 1. Intake

Ask **only what is missing**, in **one short message**:

- topic or passage
- specialization: theology · apologetics · evangelistic · teaching/discipleship · pastoral ([specializations.md](references/specializations.md))
- audience: christian · non-christian · mixed ([audiences.md](references/audiences.md))
- output language: any. Spanish (`es`) and English (`en`) are fully validated (tradition-vocabulary check + localized default templates); for any other language (e.g. `pt`, `fr`) see step 7 and hard rule 4
- template: "Use the default template, or paste an example sermon whose structure I should copy?"

A bare request like "a sermon on grace" / "una prédica sobre la gracia" gets the intake message, not a sermon. Don't ask what the user already said; infer the language from the request when it is obvious, and confirm it in the same message.

Templates: default [big-idea.md](templates/big-idea.md) (expository, 3 points); preset [hook-book-look-took.md](templates/hook-book-look-took.md) (suits evangelistic, non-christian or mixed audiences — offer it then). If the user pastes an **example sermon**, copy only its **skeleton** — section names, order, relative length — and discard its wording, illustrations and theology entirely; the sermon then uses `template: custom` with a `sections:` list (see Output format).

### 2. Passage

If only a topic is given, propose 1–3 passages (one line each on why) and let the user choose. Don't start the text work until a passage is chosen.

### 3. Text

Run `lookup.py verse`, `variants`, `dss` and `lxx` for the passage (NT: `verse` + `variants`; OT: `verse` + `dss` + `lxx`). **Never quote from memory**: every original-language word in the sermon is copied from this session's `lookup.py` output for the exact corpus and witness it is tagged with.

### 4. Linguistics

Apply the Greek ([linguistics-greek.md](references/linguistics-greek.md)) or Hebrew/Aramaic ([linguistics-hebrew.md](references/linguistics-hebrew.md)) checks and the fallacy checks ([exegetical-fallacies.md](references/exegetical-fallacies.md)) to the key words and clauses. Run `lookup.py word` on key lemmas, including their LXX usage, and `lookup.py usage` when 1st-century meaning matters. Check every quoted reading against [contested-readings.md](references/contested-readings.md) and every variant against [text-criticism.md](references/text-criticism.md).

### 5. Comparison

Run `lookup.py compare` on the key verses and classify each divergence per [translation-comparison.md](references/translation-comparison.md) (`added-words`, `harmonization`, `capitalization`, `tradition-vocabulary`, `late-reading`, `paraphrase`). Comparison is evidence, never a majority vote on a contested reading.

### 6. Translate

Literal layer first (word-for-word in the target language, with glosses), then the natural layer — per [fidelity-rules.md](references/fidelity-rules.md) and [tradition-vocabulary.md](references/tradition-vocabulary.md). Translate from the original and the usage evidence, not from the lexicon gloss.

### 7. Structure

Fill the chosen template. Use its **localized section names** for the sermon language — `sections_es:` for Spanish, `sections:` for English — as `##` headings spelled exactly as listed, in order. For **another language**, use `template: custom` with the template's sections translated into that language in the `sections:` list (same order, last one = Notes). If an example sermon was supplied, extract only its skeleton (sections, order, relative length) — discard its wording and theology.

Length: **concise** = ~500–1300 words of body prose (quote blocks and Notes excluded), ~15–20 minutes spoken. Cut points before cutting evidence.

### 8. Adapt

Specialization shapes content ([specializations.md](references/specializations.md)); audience shapes vocabulary, illustrations and the response/call ([audiences.md](references/audiences.md)). Neither ever changes the `Literal:`/`Natural:` lines.

### 9. Write

Save to `./sermons/YYYY-MM-DD-<slug>.<lang>.md` in the current working directory (create `sermons/`; today's date; `<slug>` = short lowercase ASCII words joined by hyphens, e.g. `2026-11-18-amado-no-condenado.es.md`; if the name exists, append `-2`). Use the format in [sermon-output.md](templates/sermon-output.md). Also show the sermon in chat.

### 10. Verify

Run `python3 scripts/check_sermon.py ./sermons/<file>.md` (by its path in the skill folder). **Fix every ERROR and run it again until it exits 0** before presenting the sermon as done. Then handle each WARN: length; contested ref without an options note in Notes; 3+ untagged original-language words in prose; one-word segments around `…` or too many `…` (stitching risk — quote a contiguous phrase or split the quote); tradition vocabulary not checked (languages other than es/en — say so in Notes). Never "fix" an ERROR by changing the quoted text to something `lookup.py` did not print — re-run `lookup.py` and copy, or drop the quote. Exit 2 = DB missing (see Paths and setup).

## Hard rules

1. **Never quote Hebrew, Aramaic or Greek from memory.** Copy it from `lookup.py` output for the exact corpus + witness in the tag. If the tool did not print it, it does not go in the sermon.
2. **Tag every quote** `[CORPUS[:WITNESS] Ref]`:
   - corpora `HEB` `ARC` `GRC` (NT) `LXX` `DSS` `EXT`; defaults `GRC`→SBL, `HEB`/`ARC`→WLC, `LXX`→Rahlfs;
   - tag `ARC` for the Aramaic portions — Dan.2.4b–7.28, Ezra.4.8–6.18, Ezra.7.12–26, Jer.10.11 (`verse` morphology codes start with `A` there) — and `HEB` elsewhere in the OT;
   - no space after the colon (`[GRC:TR 1John.5.7]`, not `[GRC: TR …]`); one space before the ref;
   - `DSS` and `EXT` always name a witness: `[DSS:1QIsaa Isa.53.11]`, `[EXT:Josephus Ant.1.222]`, `[EXT:Philo Abr.1.1]`;
   - a late reading names its witness (`[GRC:TR …]`, `[GRC:Byz …]`), so a TR-only text never passes as plain `[GRC …]` (= SBL); Ketiv is `[HEB:Ketiv …]`;
   - refs are `Book.Chapter.Verse` (OSIS book IDs, KJV verse numbering); ranges only within one chapter and ≤ 50 verses (`John.3.16-17`); no chapter-only refs;
   - if a witness omits a verse inside a range, split the quote into per-verse quotes for the verses it has;
   - the quoted text must be a contiguous run of that witness's verse text; `…` may elide, but never stitch single words together.
3. **Two lines after every quote**: `Literal:` then `Natural:`, in the sermon language.
4. **No tradition vocabulary on `Literal:`/`Natural:` lines** — any term in [tradition-vocabulary.md](references/tradition-vocabulary.md) for that language (e.g. *church/iglesia* for ἐκκλησία, *baptize/bautizar* for βαπτίζω) is an error there. Use the plain rendering; name and discuss the traditional term in prose or Notes. For a language other than es/en the validator still rejects any es/en list term on those lines, but cannot check that language's own church vocabulary: apply the EN/ES lists by analogy (render the plain meaning, not the church term) and state in Notes that the translation lines were not machine-checked for tradition vocabulary.
5. **Capitalization**: manuscripts of the period have no case distinction. No capitals added to πνεῦμα ἅγιον / רוּחַ ("holy spirit", "espíritu santo"); θεός/אֱלֹהִים → "God/Dios" only where target-language grammar treats it as a name (e.g. אֱלֹהִים with a singular verb, as in Gen.1.1 and Gen.1.26 — there the contested part is the plural "let us … our", not "God"); where the form is anarthrous and the sense debated (John.1.1c, Heb.1.8) or the word takes plural agreement (Ps.82.6), show the options ("God / divine / a god / gods") instead of deciding by a capital letter; no reverential capitals on pronouns or titles ([fidelity-rules.md](references/fidelity-rules.md) §4).
6. **Show the options at contested readings** ([contested-readings.md](references/contested-readings.md)): the original, each option with its grammatical/lexical/textual basis, and what the immediate context favors — as evidence, not verdict. Never pick silently, in either direction; never pick what suits a doctrine or an anti-doctrine. "The text allows both" is a valid finding.
7. **Usage claims only from this session's `lookup.py` output** — occurrence counts, semantic domains, "the LXX uses X where the Hebrew has Y", Josephus/Philo/papyri usage. Report the tool's caveats (LXX/Hebrew figures from `word` are same-verse co-occurrence, not alignment).
8. **Glosses are hints, not translations.** Lexicon and tool glosses can carry tradition vocabulary or an interpretation (e.g. ἅγιος "saint", ἔθνη "Gentiles", ᾍδης "hell", βαπτίζω "baptize"). Translate from the original form, its morphology and the usage evidence.
9. **No doctrine sources**: no creeds, confessions, councils, church fathers as interpreters, systematic theologies, commentaries, study-Bible notes, unfoldingWord notes, or denominational statements — not cited, not paraphrased. A church father may appear only as a dated text-critical witness.
10. **DSS text is extant letters only.** Letters in [brackets] inside a word are editors' reconstructions, not on the scroll — never quote them as scroll text; `dss` diffs are consonant-only and a "delete" may be a lacuna, not an omission.
11. **EXT text flagged `editor_bracketed`** by `lookup.py` must be labelled as editor-bracketed (editorial addition), never presented as plain Josephus/Philo. Josephus and Philo are evidence for word usage and background only — never Philo's allegory, never interpretation.
12. **Papyri (Moulton–Milligan) is noisy OCR** of a printed lexicon: paraphrase what the entry reports, with that caveat; never quote it as verified ancient text.
13. **No word-study fallacies**: no root fallacy ("ekklēsia = called-out ones"), no illegitimate totality transfer, no anachronism ("dynamis = dynamite"), no "aorist = once for all". If the user asks for one, decline the move and give the evidence-based reading ([exegetical-fallacies.md](references/exegetical-fallacies.md)).
14. **Say what the evidence shows and stop.** "The data has no witness for X" is a valid finding; don't fill gaps with confident guesses or present a scholarly majority as the text's own voice.

## `lookup.py` cheat sheet

JSON by default; add `--format text` for a compact human view (put it before or after the subcommand). Refs accept OSIS (`John.3.16`), English or Spanish names (`Juan 3:16`, `1 Jn 5:7`). Exit 1 = unknown ref/witness, exit 2 = DB missing.

| command | gives | example |
|---|---|---|
| `verse <ref> [--corpus C] [--witness W]` | verse text + per-word lemma, Strong's, morphology, gloss. Corpus is inferred from the book (OT→`hebot`, NT→`grnt`); `--corpus lxx\|dss\|ext` for others | `verse John.1.1` · `verse John.1.18 --witness THGNT` · `verse Ps.100.3 --witness Ketiv` · `verse Judg.11.34 --corpus lxx` · `verse Isa.53.11 --corpus dss --witness 1QIsaa` · `verse Ant.1.222 --corpus ext --witness Josephus` |
| `interlinear <ref>` | surface + gloss per word — source for the `Literal:` layer | `interlinear John.3.16-17` |
| `variants <ref>` | NT readings by edition (SBL, NA, THGNT, WH, Treg, Byz, TR) with an early/late label — always report the edition list, not just the label | `variants 1John.5.7` |
| `word <lemma\|strongs>` | lexicon gloss/definition, semantic domains, NT counts, LXX co-occurrence with Hebrew words | `word ἐκκλησία` · `word H7225` |
| `usage <lemma>` | 1st-century usage: counts and sample contexts in NT, LXX, Josephus, Philo, plus the Moulton–Milligan entry | `usage ἐκκλησία` |
| `compare <ref> [--versions V,…]` | original vs published translations (KJV, YLT, BSB, WEB, RV1909, user CSVs) | `compare Matt.16.18 --versions KJV,BSB,RV1909` |
| `dss <ref>` | each Dead Sea Scroll's extant text vs WLC (consonants only) | `dss Isa.53.11` |
| `lxx <ref>` | LXX witnesses (Rahlfs, RahlfsA, RahlfsTh) with WLC alongside | `lxx Isa.45.23` |
| `search <lemma\|strongs> [--corpus C] [--limit N]` | refs where a lemma occurs | `search μονογενής --corpus grnt` |

Witnesses: GRC `SBL` (default) `NA` `THGNT` `WH` `Byz` `TR`; HEB/ARC `WLC` (default) `Ketiv`; LXX `Rahlfs` (default) `RahlfsA` `RahlfsTh`; DSS manuscript sigla (`1QIsaa`, `4Q56` …; `dss <ref>` shows which scrolls have the verse); EXT `Josephus` (`Ant`, `War`, `Life`, `AgAp`) and `Philo` (e.g. `Abr`, `Mos`, `SpecLeg`).

## Output format

Full worked example (Spanish, validates): [sermon-output.md](templates/sermon-output.md).

```markdown
---
passage: John.3.16-17
language: es
specialization: evangelistic
audience: mixed
template: big-idea
date: 2026-11-18
---

# Title — Juan 3:16–17

## Introducción
…
> [GRC John.3.17] οὐ γὰρ ἀπέστειλεν ὁ θεὸς τὸν υἱὸν εἰς τὸν κόσμον ἵνα κρίνῃ τὸν κόσμον
> Literal: no pues envió el Dios al hijo al mundo para-que juzgue al mundo
> Natural: Porque Dios no envió al hijo al mundo para juzgar al mundo,
…
## Notas
- variants, contested readings with options, translation-comparison findings, commands used
```

- Frontmatter keys: `passage, language, specialization, audience, template, date`. `language` is a bare language code (`es`, `en`, `pt`, `pt-BR`; names like `Spanish`/`español` also work) — anything else (e.g. `Spanish (es)`) is an error; `specialization` one of `theology | apologetics | evangelistic | teaching | pastoral`; `audience` one of `christian | non-christian | mixed`; `template` is a file name from `templates/` (`big-idea`, `hook-book-look-took`) or `custom`.
- `template: custom` (skeleton copied from a user's example, or any language other than es/en) adds `sections: Name 1, Name 2, …, Notes` to the frontmatter, in the sermon language; each becomes a `##` heading. The **last** listed section is treated as Notes (e.g. `Notas`, `Anotações`).
- Each quote block: tag line, then `> Literal: …`, then `> Natural: …`. Original-language words in prose should be short (one or two words); anything longer goes in a tagged quote.
- The last section is **Notes** (in the sermon language: `Notes`, `Notas`, or the last `sections:` name of a custom template): variants (with edition lists), every contested reading quoted with its options, translation-comparison findings (format in [translation-comparison.md](references/translation-comparison.md)), and the `lookup.py` commands used. Write refs in Notes as OSIS (`John.1.1`) or English/Spanish names (`John 1:1`, `Juan 1:1`) so the validator sees the contested-reading note.

## References

| file | use it for |
|---|---|
| [fidelity-rules.md](references/fidelity-rules.md) | quoting, two-layer translation, contested readings, capitalization, usage claims, no doctrine sources |
| [linguistics-greek.md](references/linguistics-greek.md) | aspect, voice, article/Colwell, genitives, participles, conditionals, Semitisms, LXX as NT lexicon |
| [linguistics-hebrew.md](references/linguistics-hebrew.md) | verb forms, construct chains, parallelism, idioms, divine names, *hesed*, Ketiv/Qere, LXX/DSS alongside MT |
| [exegetical-fallacies.md](references/exegetical-fallacies.md) | root, etymological, totality transfer, anachronism, word–concept, selective evidence, overspecification |
| [translation-comparison.md](references/translation-comparison.md) | comparing published versions and classifying divergences |
| [text-criticism.md](references/text-criticism.md) | witnesses in the DB, early vs late, how to report variants |
| [tradition-vocabulary.md](references/tradition-vocabulary.md) | banned terms on translation lines (EN/ES) and their plain renderings |
| [contested-readings.md](references/contested-readings.md) | refs where options must be shown, with the options |
| [specializations.md](references/specializations.md) | theology, apologetics, evangelistic, teaching/discipleship, pastoral |
| [audiences.md](references/audiences.md) | christian, non-christian, mixed |

| template | use |
|---|---|
| [big-idea.md](templates/big-idea.md) | default: expository Big Idea, 3 points |
| [hook-book-look-took.md](templates/hook-book-look-took.md) | preset for evangelistic / non-christian / mixed audiences |
| [sermon-output.md](templates/sermon-output.md) | the file format `scripts/check_sermon.py` expects — a complete example |

## Scripts

| script | use |
|---|---|
| `scripts/lookup.py` | every original-language word, gloss, variant, usage count and comparison (cheat sheet above) |
| `scripts/check_sermon.py <file>…` | validator (step 10): exit 1 on errors, 2 if the DB is missing |
| `scripts/build_db.py` | builds `data/bible.db` from the vendored `sources/` (offline) |
| `scripts/fetch_sources.sh` | maintenance only: refresh or `--check` the vendored sources |
| `scripts/check_lxx_alignment.py` | maintenance only: LXX versification sanity check |
| `scripts/lint_skill.py` | maintenance only: lints this SKILL.md |

Install or update: run `install.sh` from the skill folder — it builds the DB if missing and symlinks the skill into each agent's skills directory.
