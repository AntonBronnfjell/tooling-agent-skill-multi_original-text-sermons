<div align="center">

# original-text-sermons

**Concise, preachable sermons straight from the Hebrew/Aramaic and Greek — no doctrine, no tradition, only fidelity to the text.**

<p>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="Standard library only" src="https://img.shields.io/badge/dependencies-stdlib%20only-success">
  <img alt="Tests" src="https://img.shields.io/badge/tests-421%20passing-success">
  <img alt="Evals" src="https://img.shields.io/badge/evals-15%20cases%2C%2081%2F81%20assertions-success">
  <img alt="Code license MIT" src="https://img.shields.io/badge/code-MIT-blue">
  <img alt="Data non-commercial" src="https://img.shields.io/badge/data-personal%20%2F%20non--commercial-orange">
</p>

<p>
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-skill%20%2B%20hook-D97757">
  <img alt="Cursor" src="https://img.shields.io/badge/Cursor-skill%20%2B%20hook-000000">
  <img alt="GitHub Copilot" src="https://img.shields.io/badge/Copilot-skill-24292F?logo=github">
  <img alt="Google Antigravity" src="https://img.shields.io/badge/Antigravity-skill-4285F4?logo=google&logoColor=white">
</p>

<a href="#what-it-does">What it does</a> ·
<a href="#install">Install</a> ·
<a href="#usage">Usage</a> ·
<a href="#tooling">Tooling</a> ·
<a href="#data-sources">Data sources</a> ·
<a href="#known-limitations">Limitations</a> ·
<a href="#use-and-license">License</a>

</div>

---

An LLM-agnostic agent skill (Claude Code, Cursor, Copilot, Google Antigravity, or any agent that reads markdown and runs `python3`). It translates fresh into **any language** — Spanish and English fully validated (tradition-vocabulary check and localized templates); other languages use a custom localized template and get a warning that tradition vocabulary was not machine-checked.

> [!IMPORTANT]
> The skill holds **no doctrinal position**. Where the text honestly allows more than one reading, it shows the original, each option and what the context favors — never picking silently, in either direction.

## What it does

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>🔒 Quotes are verified, not remembered</h4>
      Every Hebrew/Greek quote comes from a local SQLite database and is checked by <code>scripts/check_sermon.py</code>: quote blocks and inline-tagged phrases must match the tagged edition and verse; any untagged run of two or more original-language words — in the body or in Notes — is an error.
    </td>
    <td width="50%" valign="top">
      <h4>🪜 Two-layer translation</h4>
      A literal word-for-word line, then a natural line. Later church vocabulary (<i>church</i>, <i>baptize</i>, <i>iglesia</i>, <i>bautizar</i>…) is not allowed on either — the plain meaning goes in the line, tradition terms may be discussed in prose.
    </td>
  </tr>
  <tr>
    <td valign="top">
      <h4>⚖️ Contested readings show the options</h4>
      John 1:1c, <i>pistis Christou</i>, Gen 1:26, Matt 28:19 / Acts 2:38 "the name", 1 John 5:7… each with its grammatical, lexical and textual basis — no verdict.
    </td>
    <td valign="top">
      <h4>📜 1st-century evidence</h4>
      LXX as the lexicon of NT Greek, Dead Sea Scrolls (extant letters only), Josephus, Philo and papyri usage; six printed Greek editions side by side (SBL/NA/THGNT/WH vs Byz/TR); where published translations diverge.
    </td>
  </tr>
  <tr>
    <td valign="top">
      <h4>🚫 No doctrine sources</h4>
      No creeds, commentaries, church fathers as interpreters, study-Bible notes or denominational statements.
    </td>
    <td valign="top">
      <h4>🎯 Audience &amp; specialization aware</h4>
      Theology, apologetics, evangelistic, teaching, pastoral × christian, non-christian, mixed — using the default <i>Big Idea</i> template, the <i>Hook-Book-Look-Took</i> preset, or the skeleton of an example sermon you paste.
    </td>
  </tr>
</table>

See [SKILL.md](SKILL.md) for the workflow the agent follows and [AGENTS.md](AGENTS.md) for contributors.

## Install

**Requirements:** Python 3.9+ (standard library only, `lzma` built in) · ~500 MB free disk for the built database (`data/bible.db`, ~400 MB).

```bash
git clone https://github.com/AntonBronnfjell/tooling-agent-skill-multi_original-text-sermons.git \
  ~/Development/anton.social/tooling-agent-skill-multi_original-text-sermons
cd ~/Development/anton.social/tooling-agent-skill-multi_original-text-sermons
./install.sh            # build data/bible.db if missing, symlink into each agent's skills dir, wire hooks
./install.sh --status   # show where it is installed
./install.sh --uninstall
```

`install.sh` symlinks the repo (one copy on disk) into each agent's skills directory that exists:

| Host | Skills directory | Validator hook |
|---|---|---|
| Claude Code | `~/.claude/skills/original-text-sermons` | `PostToolUse` hook declared in `SKILL.md` frontmatter — active once the skill is invoked; errors block, warnings are returned to the model |
| Cursor | `~/.cursor/skills/…` | `afterFileEdit` entry merged into `~/.cursor/hooks.json` (output may not reach the agent) |
| Copilot | `~/.copilot/skills/…` | none — SKILL.md step 10 runs the validator |
| Google Antigravity | `~/.gemini/config/skills/…` (created when `~/.gemini` exists) | none — SKILL.md step 10 runs the validator |
| Other agents | `~/.agents/skills/…` | none — SKILL.md step 10 runs the validator |

<details>
<summary><b>Claude hook details and manual fallback</b></summary>

The Claude hook command searches `.claude/skills` (project), `~/.claude/skills`, `~/.agents/skills`, `~/.copilot/skills` and `~/.cursor/skills` for the validator. If skill-scoped hooks are disabled (for example an organisation lock), merge `hooks/claude-code.json` into `~/.claude/settings.json` manually. See [hooks/README.md](hooks/README.md).
</details>

To build the database by hand: `python3 scripts/build_db.py` (offline; reads the vendored `sources/`). Set `OTS_DB=/path/to/bible.db` to keep it elsewhere.

## Usage

Ask your agent, for example:

- *"Write a sermon on John 3:16–17 for a mixed audience, in Spanish"*
- *"Prepara una prédica evangelística sobre Lucas 15"*
- *"Give me a word study on ekklesia — how was it used in the first century?"*

Sermons are saved to `./sermons/YYYY-MM-DD-<slug>.<lang>.md` in your working directory and validated before they are shown. A quote block looks like this:

```markdown
> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος
> Literal: and God was the word
> Natural: …options shown in Notes…
```

<details>
<summary><b>Your own translations</b></summary>

Drop modern translations you own as CSV files in `sources/user/` (format in `sources/user/README.md`; the directory is gitignored) and rebuild the DB; they appear in `lookup.py compare`.
</details>

## Tooling

```bash
python3 scripts/lookup.py --format text verse John.1.1          # text + morphology + glosses
python3 scripts/lookup.py --format text variants 1John.5.7      # readings by edition, early vs late
python3 scripts/lookup.py --format text usage ἐκκλησία          # NT (per edition), LXX, Josephus, Philo, papyri
python3 scripts/lookup.py --format text compare Matt.16.18      # published translations side by side
python3 scripts/lookup.py --format text dss Isa.53.11           # Dead Sea Scrolls vs Masoretic text
python3 scripts/check_sermon.py sermons/2026-11-18-example.es.md  # validate a sermon file
python3 -m unittest discover -s tests -v                        # tests
python3 scripts/lint_skill.py                                   # lint SKILL.md
```

Other subcommands: `interlinear`, `word`, `lxx`, `search`. Run `python3 scripts/lookup.py <command> --help`.

## Data sources

All sources are vendored (xz-compressed, pinned) under `sources/`; `sources/MANIFEST.json` records each file's upstream, commit/version, sha256 and license note. The licenses below are those of the data, not of this repo's code.

<details open>
<summary><b>Sources and licenses</b></summary>

| source | gives | license (from `MANIFEST.json`) |
|---|---|---|
| [STEPBible Data](https://github.com/STEPBible/STEPBible-Data) — TAHOT, TAGNT, TVTMS | Hebrew/Aramaic OT (Leningrad/WLC) with morphology and Ketiv/Qere; Greek NT with edition markers (NA, SBL, THGNT, WH, Byz, TR); versification | CC BY 4.0, STEPBible.org (Tyndale House Cambridge); attribution required |
| STEPBible TBESH | brief Hebrew lexicon | CC BY 4.0, STEPBible.org; the Meaning column is from the Abridged BDB by Online Bible (c) Larry Pierce — upstream says permission should be gained from Online Bible before these definitions are published |
| STEPBible TBESG | brief Greek lexicon | CC BY 4.0, STEPBible.org; definitions from Abbott-Smith (public domain), gaps filled from edited Middle Liddell |
| [MACULA Greek](https://github.com/Clear-Bible/macula-greek) | syntax, Louw–Nida domains, SBLGNT text | MACULA Greek data CC BY 4.0 (Clear Bible); SBLGNT text CC BY 4.0 (Society of Biblical Literature / Logos) |
| [MACULA Hebrew](https://github.com/Clear-Bible/macula-hebrew) | syntax, SDBH domains, LXX Greek Strong's links | MACULA Hebrew data CC BY 4.0 (Clear Bible); WLC text public domain; see upstream LICENSE.md for glosses |
| [LXX Rahlfs 1935](https://github.com/eliranwong/LXX-Rahlfs-1935) | Septuagint with morphology | CC BY-NC-SA 4.0 (Eliran Wong); derivative of CATSS/CCAT LXXM data, whose terms ask users to file the CCAT user declaration; **personal non-commercial use only** |
| [ETCBC DSS](https://github.com/ETCBC/dss) (biblical scrolls only) | Dead Sea Scrolls per manuscript | CC BY-NC 4.0 (Abegg, Bowley, Cook data; ETCBC Text-Fabric conversion) |
| [Perseus canonical-greekLit](https://github.com/PerseusDL/canonical-greekLit) — Josephus | 1st-century Greek usage (Niese edition) | CC BY-SA 4.0 (Perseus Digital Library) |
| [First1KGreek](https://github.com/OpenGreekAndLatin/First1KGreek) — Philo | 1st-century Greek usage (Cohn–Wendland edition) | CC BY-SA 4.0 (First1KGreek / Open Greek and Latin) |
| [Moulton & Milligan, *Vocabulary of the Greek Testament*](https://archive.org/details/vocabularyofgree00mouluoft) | papyri and inscription usage per lemma (noisy OCR) | Public domain (Hodder & Stoughton 1914–1929; scan University of Toronto / Internet Archive 2008) |
| [Robinson–Pierpont Byzantine text](https://github.com/byztxt/byzantine-majority-text) | Byzantine verse text (2018 edition) | Public domain (CC0 1.0; repository LICENSE: 'IN THE PUBLIC DOMAIN') |
| [Scrivener 1894 (byztxt)](https://github.com/byztxt/greektext-scrivener) and [eBible.org grctr](https://ebible.org/details.php?id=grctr) | Textus Receptus verse text; grctr checked word-for-word against Scrivener 1894 (unaccented) | Scrivener: Public domain (repository README: 'Public Domain. Copy freely.'); grctr: Public domain (eBible.org: 'firmly in the Public Domain due to its age'; Adam Boyd's annotations dedicated to the public domain) |
| [Faithlife SBLGNT](https://github.com/Faithlife/SBLGNT) | SBL text cross-checked per verse by `scripts/check_sblgnt.py` | SBLGNT text CC BY 4.0 (Society of Biblical Literature and Faithlife); apparatus not vendored |
| [eBible.org](https://ebible.org/) — KJV, YLT, BSB, WEB, RV1909 | comparison translations | Public domain |

Listed in the manifest but not vendored: LXX Swete 1930 (CC BY-NC-SA 4.0) and Reina 1569 (public domain; no digital text found).
</details>

## Known limitations

> [!WARNING]
> - **TR/Byzantine text** now comes from printed editions: Byzantine from Robinson–Pierpont (2018); TR from eBible grctr, verified word-for-word against Scrivener 1894 (unaccented). TR verses without ground truth are flagged and the checker warns; 5 known-scrambled TR verses are rejected. Verse breaks follow the KJV where editions differ (flagged, informational).
> - The `variants` word-order entries for TR/Byzantine come from TAGNT word data and can differ from the printed verse text (e.g. 1 Tim 1:1).
> - **SBL text** is verified against Faithlife SBLGNT (`scripts/check_sblgnt.py`). Romans ends at 16:24 in the published SBLGNT file (no 16:25–27); the data reflects that.
> - The data holds **printed editions**, not individual manuscripts.
> - Moulton & Milligan is cleaned but still OCR and is never quoted as verified text. Reina 1569 is still unavailable (searched 2026-11-19).

Evals: 15 cases, 81/81 assertions (iteration 4) — see [evals/RESULTS.md](evals/RESULTS.md).

The plan to close these gaps is in [docs/superpowers/plans/2026-11-19-gap-closure.md](docs/superpowers/plans/2026-11-19-gap-closure.md).

## Use and license

> [!NOTE]
> This skill is built for **personal, non-commercial use** — some of the data (LXX, Dead Sea Scrolls) is licensed non-commercial only, and the TBESH lexicon definitions need permission before publication. Respect each source's license (attribution for CC BY data; share-alike for CC BY-SA) if you share anything derived from it.

The code (scripts, tests, references, templates) is MIT-licensed — see [LICENSE](LICENSE). The data under `sources/` and the built `data/bible.db` keep their own licenses, listed above.
