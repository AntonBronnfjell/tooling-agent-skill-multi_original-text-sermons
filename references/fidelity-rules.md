# Fidelity rules

The skill's only loyalty is to the text, as close to the 1st century as surviving evidence allows. It holds no doctrinal position. These rules apply to every sermon, word study and answer.

## 1. Never quote from memory

- Every Hebrew, Aramaic, Greek, LXX, DSS, Josephus or Philo word comes from `scripts/lookup.py` output in the **same session**. If the tool did not print it, it does not go in the sermon.
- Quote blocks use the tag grammar `[CORPUS[:WITNESS] Ref]` (corpora `HEB ARC GRC LXX DSS EXT`; defaults GRC→SBL, HEB/ARC→WLC, LXX→Rahlfs; DSS and EXT require a witness). The quoted text must be a contiguous substring of `lookup.py verse <ref> [--corpus …] [--witness …]` for that witness; `…` may elide.
- A late reading always names its witness: `[GRC:TR 1John.5.7]`. A plain `[GRC …]` tag is the SBL text.
- DSS text holds extant letters only; letters in [brackets] are editors' reconstructions — say so if you use them. Josephus words the tool flags as editor-bracketed are not quoted as Josephus.
- Moulton–Milligan papyri entries are noisy OCR of a printed lexicon. Use only the papyrus citations the entry reports, paraphrased; never quote it as verified ancient text, and never use the entry's own commentary or the later scholars it cites (e.g. the ἐκκλησία entry opens with the lexicographers' view of the word's "Biblical history" and a reference to Hort — that is commentary, not papyrus evidence).
- Lexicon glosses from the tool (e.g. ἅγιος "holy: saint", ᾍδης "hell: Hades", βαπτίζω "to baptize", 1John.3.9 ἁμαρτάνειν glossed "to continue sinning") are aids, not translations. Some carry later vocabulary or an interpretation; check them against morphology and usage before using them.

## 2. Two-layer translation

Every quote block is followed by two lines:

```
> [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος
> Literal: and God/god was the word
> Natural: …
```

- `Literal:` word-for-word in the target language, original word order where readable; slashes for real alternatives; square brackets for words the target language needs but the text lacks.
- `Natural:` fluent target language, faithful in meaning. No added words the text does not imply; mark any that grammar forces.
- Neither line may contain a term from `tradition-vocabulary.md` for that language (machine-checked). Use the plain rendering; discuss the traditional term in prose or Notes if useful.
- Standard lexical equivalents are not tradition vocabulary. Example: μετανοέω may be rendered "repent / arrepentirse", "turn", or "change one's mind"; when the sense matters, show its range from usage (`lookup.py word μετανοέω`, `usage μετανοέω`: in LXX verses it co-occurs with נָחַם 14× and שׁוּב 9×) and say which the context shows. Don't define it from its parts (μετά + νοέω) — see `exegetical-fallacies.md` §1. The same applies to δικαιόω ("in the right / made or declared right" — say which the context shows).

## 3. Contested readings: show the options

Where grammar, vocabulary or the manuscripts honestly allow more than one reading (`contested-readings.md`), show: the original, each option with its grammatical/lexical/textual basis, and what the immediate context favors — as evidence, not verdict. Never resolve silently in either direction, and never pick the option that suits a doctrine (or an anti-doctrine). If the evidence does not settle it, say "the text allows both".

## 4. Capitalization rule

Early Hebrew and Greek manuscripts make no distinction between upper and lower case (they are written in one letter-case); every capital in a translation is the translator's decision. Say it that way — not "they had no capital letters" (majuscule manuscripts are written entirely in capitals).

One rule covers θεός / אֱלֹהִים and κύριος, on `Literal:`/`Natural:` lines **and in the preacher's own prose**, and it is applied the same way whoever the word refers to (God, Jesus, a human master):

- **θεός / אֱלֹהִים: name vs common noun, by the target language's grammar.** A word used as a proper name takes a capital: ὁ θεός as the subject or referent of a clause (John.3.16 → "Dios"), אֱלֹהִים with a singular verb (Gen.1.1 בָּרָא, Gen.1.26 וַיֹּאמֶר → "God"; in Gen.1.26 what is contested is the plural "let us … our", not "God"). A common noun stays lower case ("a god", "gods").
- **κύριος / κύριε: lower case by default, both casings where it is contested.** Lower case is the default where κύριος is a common noun or title, as the language writes any title ("the king", "el maestro"):
  - a predicate: "X is lord" / "X es señor";
  - "my lord", masters and owners, parables;
  - address: κύριε → "lord", "señor", "sir" (the sense the context shows);
  - plain prose and narration: "the lord said", "el señor dijo".

  But wherever κύριος quotes or echoes a YHWH text, or the body shows the identification with options (e.g. Phil.2.11, Rom.10.9-13, 1Cor.8.6, Acts.2.21, Acts.2.36, Heb.1.10), show **both casings** — "lord / Lord", "señor / Señor" — and report from `lxx <ref>` / `verse <ref>` output whether κύριος stands where the Hebrew has יהוה (e.g. Heb.1.10 quotes Ps.102.25, where the LXX has κύριε and the WLC has no יהוה), plus the senses the shown `usage κύριος` contexts display. **Neither casing decides** whether a NT κύριος stands for the divine name. For any other sense (address "sir", master/owner…), `search`/`verse` an example first. Report; give no verdict.
- **Coordinated pairs get the same casing.** Where one phrase joins the two words (Byz Acts.20.28 τοῦ κυρίου καὶ θεοῦ; John.20.28 ὁ κύριός μου καὶ ὁ θεός μου) don't capitalize one and not the other ("del señor y Dios"); show the options — "of the lord and god / of the Lord and God" — and say capitals are the translator's choice.
- **Contested θεός: show the options.** Where the form is anarthrous and the sense is debated (John.1.1c, Heb.1.8) or the word takes plural agreement (1Sam.28.13 אֱלֹהִים … עֹלִים, Ps.82.6 אֱלֹהִים אַתֶּם), show "God / divine / a god / gods" instead of choosing by capital letter.
- **No capitals added to πνεῦμα ἅγιον / רוּחַ**: write "holy spirit" / "espíritu santo" on `Literal:`/`Natural:` lines. If the sermon discusses how others capitalize it, do so in prose.
- No reverential capitals on pronouns or titles (he/him, hijo, palabra, él). "Son/Hijo", "Word/Verbo", "the LORD", "el Señor" as published capitals are a translation choice: quote them as such and mention them in comparison notes.
- State the convention in one line in Notes (e.g. "Capitals: names capitalized; κύριος lower case by default for every referent — a typographic convention that claims nothing about who is meant; both casings shown at Phil.2.11; manuscripts make no upper/lower-case distinction").
- Capitalization is not machine-checked (that would force a side on contested readings); this rule is enforced by review and evals.

## 5. Usage claims only from the tool

Occurrence counts, semantic domains, "the LXX uses X for Hebrew Y", Josephus/Philo/papyri usage: only from `lookup.py word`, `usage`, `search`, `lxx` output in the same session. Report what the tool reports, including its caveats — e.g. `word` prints LXX/Hebrew **same-verse co-occurrence, not alignment**, so say "in the LXX, ἐκκλησία co-occurs with Hebrew קָהָל 66 times (same verse)", not "the LXX translates קָהָל as ἐκκλησία 66 times".

## 6. No doctrine sources

Not used, cited, or paraphrased: creeds, confessions, councils, church fathers as interpreters, systematic theologies, commentaries, study-Bible notes, unfoldingWord notes, denominational statements. A church father may be mentioned only as a **text-critical witness** (what text he quoted, with date), never for what he taught — see Matt.28.19 in `contested-readings.md`.

## 7. Background allowed, allegory not

- Allowed: 1st-century history, geography, customs, Second Temple Jewish practice, and word usage in Josephus, Philo, LXX, DSS and papyri — as evidence for what words meant then.
- Not allowed: Philo's allegorical interpretations (or anyone's) as a key to the text's meaning; later meanings read back into earlier words (see `exegetical-fallacies.md`, anachronism).

## 8. Scope of claims

Say what the evidence shows and stop. "The data has no witness for X" is a valid finding. Do not fill gaps with confident guesses, and do not present a scholarly majority as the text's own voice.

- Scope summaries to the examples shown ("in the 10 contexts shown…"); no "never / always / all hearers / everyone in the 1st century", and no claims about what hearers thought.
- At contested readings, no weighting words (leans, favors, independent support, more reliable) unless the tool output shows it; report every witness the tool returns, not a selection.
- Background facts no lookup produced (dates, labels such as "hymn") are marked as background or left out. Exception: the brief who/where/when setting sentence before the text (`audiences.md`) is permitted background (§7) if it stays general ("in the first century") and claims nothing contested.
- Examples in these reference files are illustrations: re-run the lookup in the session before repeating one.
