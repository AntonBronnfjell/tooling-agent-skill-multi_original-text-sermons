# Text criticism

Goal: let the listener know where the wording of the passage is uncertain or late, using the witnesses in the DB. Report evidence; don't adjudicate theology through it.

**The NT data holds printed editions** (NA28, SBL, THGNT, WH, Byz, TR), not individual manuscripts. Say so when you report a variant, and never claim manuscript evidence ("the earliest manuscripts omit…", "Codex X reads…") the tools don't show. The `variants` label "early"/"late" describes which editions print a reading.

## Witnesses in the DB

| corpus | witnesses | notes |
|---|---|---|
| GRC (NT) | SBL (default), NA, THGNT, WH, Byz, TR | NA, SBL, THGNT, WH = critical editions built mainly on early manuscripts; Byz = Byzantine majority text; TR = Textus Receptus (16th-c. printed text behind KJV and RV1909) |
| HEB/ARC | WLC (default; Qere-based where the Masoretes marked one), Ketiv | Masoretic text, Leningrad codex (c. 1008) |
| LXX | Rahlfs (default), RahlfsA, RahlfsTh | Greek OT, translated 3rd–1st c. BC; a witness to a Hebrew text older than the Masoretic codices |
| DSS | manuscript sigla (1QIsaa, 1Q8, 4Q58 …) | biblical scrolls, c. 3rd c. BC – 1st c. AD; extant letters only, [brackets] = reconstruction |
| EXT | Josephus, Philo | 1st-c. Greek; for usage/background, not as Bible text |

"Early" vs "late" means the age of the evidence for a reading, not its value to a tradition.

## Commands

- `lookup.py variants <ref>` — NT readings by printed edition. The `editions` list is the evidence; the `class` label is "late" only when the reading's support is TR and/or Byz alone, and "early" whenever any critical edition supports it — including 19th-c. Tregelles (Treg) or Tyndale House (Tyn = THGNT). Example: John.3.16 #11 αὐτοῦ is labeled early but its support is `Treg+TR+Byz`. Always quote the edition list, not just the label.
- `lookup.py verse <ref> --witness W` — the whole verse in one edition (compare SBL with TR/Byz when a variant matters).
- `lookup.py dss <ref>` — each scroll's extant text vs WLC, consonants only; 'delete' ops may be lacunae (lost leather), not omissions.
- `lookup.py lxx <ref>` — LXX witnesses vs Rahlfs, with WLC printed for comparison (Greek and Hebrew are not diffed token by token).
- Hebrew Ketiv/Qere: `verse <ref> --witness Ketiv` vs default.

## Coverage

Run `variants` (NT) or `dss` + `lxx` (OT) over the **whole** passage, never a sample of verses. Ranges stay inside one chapter, so split at the chapter boundary: `variants John.7.53` + `variants John.8.1-11`. Then report:

- the wording differences **inside** the passage that change meaning (e.g. `variants John.8.1-11` lists edition differences in every verse of the story, 8:9 alone has 31 rows — read them all, not only 8:11), not only whether an edition brackets the whole;
- **every** witness the tool returns, each with its reading. `dss Isa.53.11` lists four scrolls: 1QIsaa and 1Q8 read אור "light" after יראה; 4Q58 has או there (`verse --witness 4Q58` shows או[ר], the ר reconstructed); 4Q56 keeps only א יסב; WLC יִרְאֶה has no object; LXX δεῖξαι αὐτῷ φῶς. 1QIsaa also reads עבדו "his servant" where 1Q8, 4Q58 and WLC read עבדי "my servant". A `…` in a scroll's text marks lost (fully reconstructed) words — 4Q58 has one after לר — so report it as a gap, not an omission. Reporting 1QIsaa alone would tilt the picture.
- Weigh nothing the tool doesn't weigh: **Wrong:** "the older witnesses lean towards 'light' — two independent kinds of witness." **Right:** "1QIsaa and 1Q8 read אור 'light' after יראה; 4Q58 has או there (`verse --witness 4Q58` shows או[ר], the ר reconstructed); 4Q56 keeps only [DSS:4Q56 Isa.53.11] א יסב; WLC יִרְאֶה has no object; LXX [LXX Isa.53.11] δεῖξαι αὐτῷ φῶς. 1QIsaa also reads עבדו 'his servant' where 1Q8, 4Q58 and WLC read עבדי 'my servant'."
- If `dss`/`lxx` answers `absent: "no DSS witness has <ref>"`, that is the finding: the corpus has no witness for that verse.

## What to report

Report a variant in the sermon when it (a) changes meaning, (b) is behind a familiar translation the audience knows, or (c) is a well-known late passage. Spelling and word-order variants that don't change meaning go to Notes only if a translation follows them.

Well-known cases (all in `contested-readings.md`):

- **1John.5.7–8** — the long text is tagged `[TR]` only, class late; SBL, NA and Byz end v.7 at οἱ μαρτυροῦντες. Quote it only as `[GRC:TR 1John.5.7]`. The TR verse text reads ἐν τῷ οὐρανῷ; the TAGNT word rows carry the erratum ἕν (see the errata list below).
- **Mark.16.9–20** and **John.7.53–8.11** — editors enclose them in [[ ]] (judged later additions). Report the `[[ ]]` markers as each edition prints them in the tool output (`verse <ref> --witness W` for NA, THGNT, WH, Byz, TR, SBL): e.g. NA, THGNT and WH print [[ before John.7.53; SBL, TR and Byz print none; the data has no THGNT text for John.8.11 (`verse John.8.11 --witness THGNT` answers `absent_in`). Report the brackets, not "missing from".
- **John.1.18** — μονογενὴς θεὸς (NA, SBL, WH, Treg) vs ὁ μονογενὴς υἱός (THGNT, TR, Byz): critical editions divide.
- **Isa.53.11** — 1QIsaa and 1Q8 read אור "light" after יראה; 4Q58 has או there (`verse --witness 4Q58` shows או[ר], the ר reconstructed); 4Q56 keeps only א יסב; WLC יִרְאֶה has no object; LXX δεῖξαι αὐτῷ φῶς. 1QIsaa also reads עבדו "his servant" where 1Q8, 4Q58 and WLC read עבדי "my servant".
- **Matt.28.19** — all editions agree on the long form; report the Eusebian citation question as stated in `contested-readings.md`, with no verdict.

Upstream errata (STEPBible TAGNT spellings the printed editions do not have). Quote the data exactly as `lookup.py` prints it — the validator only accepts that — and say in Notes that the form is a data erratum and what the printed edition reads:

- **1John.5.7** TR word rows (`interlinear`, `variants`): ἕν τῷ οὐρανῷ — ἕν "one" where the sense needs ἐν "in" (the TR verse text has ἐν).
- **Matt.17.4** TR word rows: the spelling-variant column gives μίαν in place of Μωσῇ (`variants`); the TR verse text reads καὶ Μωσῇ μίαν.
- **1Tim.1.1** TR and Byz word rows: κυριόυ (accent on the last syllable) for κυρίου; the verse text has κυρίου.
- TR and Byz verse text comes from the printed editions (Scrivener 1894, Robinson–Pierpont 2018), mapped to KJV verse numbers; a TR verse where the accented source differs from Scrivener keeps the TAGNT text and is listed in `order_flags`. Word order of THGNT/WH/NA is rebuilt from TAGNT displacement marks (`verse` adds an `order_note`; `variants` lists each edition's order). The marks reproduce SBLGNT's order in 73 of the 78 verses where SBL carries one; a few marks are inconsistent upstream (e.g. THGNT 1Cor.8.8). Verses whose order is uncertain are flagged: `verse` returns `order_uncertain: true`, and `check_sermon` warns (and errors on a TR quote of a verse known to be scrambled in the data). When an order looks wrong, show the `variants` order entry and the editions instead of building on it.

## Format

In the body, one plain sentence: "Some printed editions (TR, Byz, Tregelles) add 'his' here; NA, SBL, WH and THGNT don't."

In Notes, one bullet per variant:

```
- John.3.16 after "the son": αὐτοῦ "his" — Treg+TR+Byz ([GRC:TR John.3.16] τὸν υἱὸν αὐτοῦ); absent in SBL, NA, WH, THGNT. Tool label: early (because of Treg). Meaning: unchanged; KJV/BSB/RV1909 "his/su".
- Isa.53.11 [DSS:1QIsaa Isa.53.11] יראה אור "he will see light" — also 1Q8 אור, 4Q58 או[ר] (ר reconstructed); 4Q56 only [DSS:4Q56 Isa.53.11] א יסב; WLC יִרְאֶה without object; LXX [LXX Isa.53.11] δεῖξαι αὐτῷ φῶς. 1QIsaa עבדו "his servant" vs 1Q8, 4Q58, WLC עבדי "my servant".
```

When quoting a non-default witness in a quote block, the tag names it (`[GRC:TR …]`, `[DSS:1QIsaa …]`, `[HEB:Ketiv …]`), and the Notes say which editions support it.

## Commands used

```
lookup.py variants John.3.16 | John.1.18 | 1John.5.7 | 1John.5.8 | Mark.16.9-20 | John.7.53 | John.8.1-11 | Matt.28.19
lookup.py verse John.3.16 --witness NA|TR|Byz|WH|THGNT ; verse John.1.18 --witness THGNT|TR|NA ; verse Mark.16.9 --witness NA|SBL|WH|TR|Byz|THGNT ; verse John.7.53 --witness SBL|NA|THGNT|WH|TR|Byz ; verse John.8.11 --witness NA|THGNT ; verse 1John.5.7 --witness TR
lookup.py dss Isa.53.11 ; verse Isa.53.11 --corpus dss --witness 4Q58 ; lxx Isa.53.11 ; verse Ps.100.3 --witness Ketiv
```
