# original-text-sermons

An LLM-agnostic agent skill (Claude Code, Cursor, Copilot, or any agent that reads markdown and runs `python3`) that writes **concise, preachable sermons straight from the Hebrew/Aramaic and Greek texts**, translated fresh into Spanish or English — instead of leaning on published translations whose wording carries later doctrine and church tradition.

- **Every original-language quote comes from local data**, never from model memory, and is mechanically verified by `scripts/check_sermon.py`.
- **Two-layer translation**: a literal word-for-word line, then a natural line; later church vocabulary (*church*, *baptize*, *iglesia*…) is not allowed on either.
- **Contested readings show the options** (John 1:1c, *pistis Christou*, Gen 1:26 …) with their grammatical, lexical and textual basis — never resolved silently, in either direction.
- **Evidence from the 1st century**: LXX as the lexicon of NT Greek, Dead Sea Scrolls, Josephus, Philo and papyri usage; early vs late manuscripts (SBL/NA/THGNT/WH vs Byz/TR); where published translations diverge.
- **No doctrine sources**: no creeds, commentaries, church fathers as interpreters, study-Bible notes or denominational statements. The skill's only loyalty is fidelity to the text.
- Audience- and specialization-aware (theology, apologetics, evangelistic, teaching, pastoral × christian, non-christian, mixed), following a default template, a preset, or the skeleton of an example sermon you paste.

See [SKILL.md](SKILL.md) for the workflow the agent follows and [AGENTS.md](AGENTS.md) for contributors.

## Install

Requirements: Python 3.9+ (standard library only), `xz`-capable Python (`lzma`, built in), ~500 MB free disk for the built database (`data/bible.db`, ~400 MB).

```bash
git clone <this repo> ~/Development/anton.social/tooling-agent-skill-multi_original-text-sermons
cd ~/Development/anton.social/tooling-agent-skill-multi_original-text-sermons
./install.sh            # build data/bible.db if missing, symlink into each agent's skills dir, wire hooks
./install.sh --status   # show where it is installed
./install.sh --uninstall
```

`install.sh` symlinks the repo (one copy on disk) into `~/.claude/skills/original-text-sermons`, `~/.cursor/skills/…`, `~/.agents/skills/…` and `~/.copilot/skills/…` for the agent directories that exist, and wires the validator as a post-write hook where the host supports it.

To build the database by hand: `python3 scripts/build_db.py` (offline; reads the vendored `sources/`). Set `OTS_DB=/path/to/bible.db` to keep it elsewhere.

Then ask your agent, e.g. *"Write a sermon on John 3:16–17 for a mixed audience, in Spanish"* or *"Prepara una prédica evangelística sobre Lucas 15"*. Sermons are saved to `./sermons/YYYY-MM-DD-<slug>.<lang>.md` in your working directory.

### Your own translations

Drop modern translations you own as CSV files in `sources/user/` (format in `sources/user/README.md`; the directory is gitignored) and rebuild the DB; they appear in `lookup.py compare`.

## Tooling

```bash
python3 scripts/lookup.py --format text verse John.1.1          # text + morphology + glosses
python3 scripts/lookup.py --format text variants 1John.5.7      # readings by edition, early vs late
python3 scripts/lookup.py --format text usage ἐκκλησία          # NT, LXX, Josephus, Philo, papyri
python3 scripts/lookup.py --format text compare Matt.16.18      # published translations side by side
python3 scripts/lookup.py --format text dss Isa.53.11           # Dead Sea Scrolls vs Masoretic text
python3 scripts/check_sermon.py sermons/2026-11-18-example.es.md  # validate a sermon file
python3 -m unittest discover -s tests -v                        # tests
python3 scripts/lint_skill.py                                   # lint SKILL.md
```

Other subcommands: `interlinear`, `word`, `lxx`, `search`. Run `python3 scripts/lookup.py <command> --help`.

## Data sources

All sources are vendored (xz-compressed, pinned) under `sources/`; `sources/MANIFEST.json` records each file's upstream, commit/version, sha256 and license note. The licenses below are those of the data, not of this repo's code.

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
| [eBible.org](https://ebible.org/) — KJV, YLT, BSB, WEB, RV1909 | comparison translations | Public domain |

Listed in the manifest but not vendored: LXX Swete 1930 (CC BY-NC-SA 4.0) and Reina 1569 (public domain).

## Use and license

This skill is built for **personal, non-commercial use** — some of the data (LXX, Dead Sea Scrolls) is licensed non-commercial only, and the TBESH lexicon definitions need permission before publication. Respect each source's license (attribution for CC BY data; share-alike for CC BY-SA) if you share anything derived from it.

The code (scripts, tests, references, templates) is MIT-licensed — see [LICENSE](LICENSE). The data under `sources/` and the built `data/bible.db` keep their own licenses, listed above.
