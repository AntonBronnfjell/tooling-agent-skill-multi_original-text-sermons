# Text criticism

Goal: let the listener know where the wording of the passage is uncertain or late, using the witnesses in the DB. Report evidence; don't adjudicate theology through it.

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

- `lookup.py variants <ref>` — NT readings by edition. The `editions` list is the evidence; the `class` label is "late" only when the reading's support is TR and/or Byz alone, and "early" whenever any critical edition supports it — including 19th-c. Tregelles (Treg) or Tyndale House (Tyn = THGNT). Example: John.3.16 #11 αὐτοῦ is labeled early but its support is `Treg+TR+Byz`. Always quote the edition list, not just the label.
- `lookup.py verse <ref> --witness W` — the whole verse in one edition (compare SBL with TR/Byz when a variant matters).
- `lookup.py dss <ref>` — each scroll's extant text vs WLC, consonants only; 'delete' ops may be lacunae (lost leather), not omissions.
- `lookup.py lxx <ref>` — LXX witnesses vs Rahlfs, with WLC printed for comparison (Greek and Hebrew are not diffed token by token).
- Hebrew Ketiv/Qere: `verse <ref> --witness Ketiv` vs default.

## What to report

Report a variant in the sermon when it (a) changes meaning, (b) is behind a familiar translation the audience knows, or (c) is a well-known late passage. Spelling and word-order variants that don't change meaning go to Notes only if a translation follows them.

Well-known cases (all in `contested-readings.md`):

- **1John.5.7–8** — the long text is tagged `[TR]` only, class late; SBL, NA and Byz end v.7 at οἱ μαρτυροῦντες. Quote it only as `[GRC:TR 1John.5.7]`.
- **Mark.16.9–20** and **John.7.53–8.11** — NA28 and WH enclose them in [[ ]] (editors judge them later additions). The tool's verse text shows [[ on the first word for NA, WH, TR and Byz alike — an inherited marker, not TR/Byz's own judgment; SBL text shows none. Report the editorial brackets, not "missing from".
- **John.1.18** — μονογενὴς θεὸς (NA, SBL, WH, Treg) vs ὁ μονογενὴς υἱός (THGNT, TR, Byz): critical editions divide.
- **Isa.53.11** — 1QIsaa and LXX "light" with no counterpart in WLC.
- **Matt.28.19** — all editions agree on the long form; report the Eusebian citation question as stated in `contested-readings.md`, with no verdict.

## Format

In the body, one plain sentence: "Some later manuscripts add 'his' here; the earliest-based editions don't."

In Notes, one bullet per variant:

```
- John.3.16 after τὸν υἱὸν: αὐτοῦ "his" — Treg+TR+Byz; absent in SBL, NA, WH, THGNT. Tool label: early (because of Treg). Meaning: unchanged; KJV/BSB/RV1909 "his/su".
- Isa.53.11 [DSS:1QIsaa Isa.53.11] יראה אור "he will see light"; WLC יִרְאֶה without object; LXX δεῖξαι αὐτῷ φῶς.
```

When quoting a non-default witness in a quote block, the tag names it (`[GRC:TR …]`, `[DSS:1QIsaa …]`, `[HEB:Ketiv …]`), and the Notes say which editions support it.

## Commands used

```
lookup.py variants John.3.16 | John.1.18 | 1John.5.7 | 1John.5.8 | Mark.16.9 | John.7.53 | Matt.28.19
lookup.py verse John.3.16 --witness NA|TR|Byz|WH|THGNT ; verse John.1.18 --witness THGNT|TR|NA ; verse Mark.16.9 --witness NA|SBL|WH|TR|Byz ; verse John.7.53 --witness TR|Byz ; verse John.8.11 --witness NA
lookup.py dss Isa.53.11 ; lxx Isa.53.11 ; verse Ps.100.3 --witness Ketiv
```
