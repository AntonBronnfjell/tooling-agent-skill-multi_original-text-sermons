# Translation comparison

Purpose: show the listener where published translations say more, less, or other than the original — so the sermon's fresh translation is accountable, not idiosyncratic. Comparison is evidence; it never decides a contested reading by majority vote.

## How

1. `lookup.py compare <ref> [--versions KJV,YLT,BSB,WEB,RV1909,…]` for each key verse (user CSVs appear by their version name).
2. Read each rendering against the interlinear (`lookup.py interlinear <ref>`) and the variants (`lookup.py variants <ref>`).
3. Classify each divergence with one class below (two only when its cause is ambiguous — say why). Ignore pure style.
4. Report in the sermon's **Notes** section (format below). Mention in the body only what changes meaning for the listener.

## Divergence classes

| class | what it is | example (from `compare`) |
|---|---|---|
| `added-words` | words with no counterpart in the original, beyond what grammar forces. KJV marks many in [brackets] (its italics) — report those as the translators' own admission. | BSB Col.2.9 "in **Christ**" where the Greek has ἐν αὐτῷ "in him"; KJV Rom.9.5 "Whose **[are]** … Christ **[came]**" |
| `harmonization` | wording made to match a parallel passage (often already in the late Greek text the version follows — then also `late-reading`) | Luke.11.2 KJV/WEB "Our Father which art in heaven … Thy will be done" (Matthew's wording) where SBL has only Πάτερ, ἁγιασθήτω τὸ ὄνομά σου· ἐλθέτω ἡ βασιλεία σου; Acts.9.5 KJV/RV1909 "hard for thee to kick against the pricks" = TR σκληρόν σοι πρὸς κέντρα λακτίζειν, absent in SBL (wording of Acts.26.14) |
| `capitalization` | capitals that decide a reading the original leaves open (pronouns, *Spirit*, *Son*, *Word*, *God* vs *god*) | BSB John.3.16 "**He** gave **His** one and only **Son**"; RV1909 John.1.1 "el **Verbo**" |
| `tradition-vocabulary` | a later church term where the text has a plain word (`tradition-vocabulary.md`) | Matt.16.18 KJV/BSB "church", RV1909 "iglesia" — WEB and YLT "assembly"; Acts.2.4 KJV "Holy Ghost" |
| `late-reading` | translation follows a reading found only in late witnesses (TR/Byz) | KJV and RV1909 1John.5.7 "in heaven, the Father, the Word, and the Holy Ghost" — TR only; BSB/WEB "For there are three that testify:" |
| `paraphrase` | meaning restated so that grammar, voice, image or a contested option is lost or chosen | BSB John.3.17 "**to save** the world" for passive ἵνα σωθῇ ὁ κόσμος "that the world may be saved"; KJV Gal.2.16 "faith **of** Jesus" vs BSB/WEB "faith **in** Jesus" (each picks one option of a contested genitive) |

A contested option chosen by a translation is reported as `paraphrase` (or `capitalization`) **and** the options are shown per `contested-readings.md` — never "translation X is wrong".

## Reporting format (Notes section)

```
- John.3.16 μονογενῆ — KJV, YLT "only begotten", RV1909 "unigénito"; BSB "one and only"; WEB "only born" [paraphrase: each picks an option; see contested readings]
- John.3.16 τὸν υἱὸν — KJV, BSB "his Son", RV1909 "su Hijo": possessive matches TR/Byz αὐτοῦ, absent in SBL [late-reading or added-words]; capital S/H [capitalization]
```

One bullet per finding: ref, Greek/Hebrew word(s) copied from lookup output, version(s) and their rendering (quoted from `compare`), class in brackets. When the source of a divergence is ambiguous (e.g. a possessive could be idiom or a TR reading), name both classes and say why.

## Spanish versions

RV1909 is in the DB; user-supplied CSVs (e.g. RVR1960, NVI) appear by name. Typical Spanish findings: "iglesia", "bautizar", "arrepentíos", "Verbo", "doctrinad", "Gentiles" (`tradition-vocabulary`); "Espíritu Santo", "Hijo", "Él" (`capitalization`).

## Commands used

```
lookup.py compare John.3.16-17 | Col.2.9 | Rom.9.5 | Matt.16.18 | Acts.2.4 | 1John.5.7 | Gal.2.16 | John.1.1 | Matt.28.19 | Luke.11.2 | Acts.9.5
lookup.py verse Luke.11.2 ; verse Acts.9.5 ; verse Acts.9.5 --witness TR
lookup.py variants John.3.16 | John.3.17 | 1John.5.7 ; verse Col.2.9
```
