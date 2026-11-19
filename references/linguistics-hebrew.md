# Hebrew and Aramaic checks

Base text: WLC (`[HEB Ref]`, Aramaic portions `[ARC Ref]`), KJV verse numbering (the tool maps it — e.g. KJV Isa.9.6 = WLC 9:5, KJV Ps.19.1 = WLC 19:2). Morphology codes are the tool's: `Vqp3ms` = verb, qal, qatal (perfect), 3rd masc. sg.; `w` = wayyiqtol, `q` = weqatal, `i` = yiqtol, `j` = jussive, `c` = cohortative, `r` = participle, `a` = infinitive absolute; in nouns `c` = construct, `a` = absolute. Every example below was copied from `lookup.py` output.

## 1. Verb forms are not tenses

| form | code | typical use | caution |
|---|---|---|---|
| wayyiqtol | `w` | main line of narrative: "and he said… and there was…" | not automatically past outside narrative (Isa.9.6 וַתְּהִי sits in a prophecy) |
| qatal | `p` | completed/whole action; states; in prophecy can present a future as done ("prophetic perfect") | "past" only by context |
| yiqtol | `i` | incomplete, future, habitual, modal ("may, would") | Exod.3.14 אֶהְיֶה: "I am" / "I will be" — show both |
| weqatal | `q` | continues a yiqtol/command line, often future or habitual | Gen.2.24 וְדָבַק (`Vqq3ms`) "and he cleaves" — general, not past |
| jussive / cohortative | `j` / `c` | "let him…", "let us…" (Gen.11.3 נִלְבְּנָה `Vqc1cp`) | Gen.1.26 נַעֲשֶׂה is tagged yiqtol 1cp (`Vqi1cp`), read as "let us make" |

> [HEB Gen.1.3] וַיֹּאמֶר אֱלֹהִים יְהִי אוֹר וַיְהִי־אוֹר
> Literal: and-said God/Elohim let-be light and-was light
> Natural: then God said, "Let there be light," and there was light

In Isa.9.6 the tool's glosses show the problem: יֻלַּד is qatal (`VPp3ms`) glossed "he will be born", וַתְּהִי is wayyiqtol glossed "and it was". Translating either as simple past or simple future is a choice; say which and why.

## 2. Construct chains

Two or more nouns bound together: the first is in construct ("X of"), the last carries the definiteness of the whole chain. רוּחַ אֱלֹהִים (Gen.1.2, `Ncfsc` + noun) = "spirit/wind/breath of God" — the chain itself doesn't choose among those (see `contested-readings.md`). Adjectives in construct give idioms: אֶרֶךְ אַפַּיִם "long of nostrils" = slow to anger; וְרַב־חֶסֶד "great of loyal-love" (Exod.34.6).

## 3. Parallelism

Poetry pairs lines that restate, contrast or advance. Read the pair as one statement; don't build a doctrine on the difference between synonyms in parallel lines.

> [HEB Ps.19.1] הַשָּׁמַיִם מְסַפְּרִים כְּבוֹד־אֵל וּמַעֲשֵׂה יָדָיו מַגִּיד הָרָקִיעַ
> Literal: the-heavens recounting glory-of El and-work-of his-hands telling the-expanse
> Natural: the skies are telling God's glory; the expanse announces what his hands have made

Line A: heavens / recounting / glory of El. Line B (reversed order): work of his hands / telling / the expanse — synonymous, chiastic.

## 4. Idioms

Render the meaning, show the image in Literal: "long of nostrils" (slow to anger), "lift the face" (show favor), "know" (be intimately acquainted, also sexual), "heart" (mind/will more than emotion), "hand of" (power of), "son of X" (characterized by X), infinitive absolute + finite verb for intensity — Gen.3.16 הַרְבָּה אַרְבֶּה "increasing I will increase" = "I will greatly increase".

## 5. Hendiadys

Two nouns joined by "and" expressing one idea: Gen.3.16 עִצְּבוֹנֵךְ וְהֵרֹנֵךְ "your pain and your pregnancy" → possibly "your pain in pregnancy"; Gen.1.2 תֹהוּ וָבֹהוּ "formlessness and emptiness" → "a formless void". Where hendiadys is possible but not certain, give both renderings.

## 6. Divine names and titles

- **יְהוָה (YHWH)** — the personal name. The consonants are the text; the vowels printed in WLC are the Masoretes' reading cue, not the name's original vowels. Choose and state a convention (YHWH / Yahweh / "the LORD" following the reading custom); never "Jehovah" on translation lines (`tradition-vocabulary.md`).
- **אֱלֹהִים (Elohim)** — plural in form (`Ncmpa`). With the God of Israel it normally takes singular verbs (Gen.1.1 בָּרָא `Vqp3ms`); it can also mean "gods", divine beings or judges, with plural agreement (1Sam.28.13 אֱלֹהִים … עֹלִים, plural participle; Ps.82.6 אֱלֹהִים אַתֶּם). The plural form by itself proves neither plurality nor its absence; show the grammar and the options (Gen.1.26).
- **אֵל (El)** "God, god, mighty one" (Ps.19.1, Isa.9.6 אֵל גִּבּוֹר); **אֲדֹנָי (Adonai)** "Lord/my lord" (Isa.7.14); **עֶלְיוֹן** "Most High" (Ps.82.6).
- Capitalization of "God/god" follows `fidelity-rules.md` §4.

## 7. חֶסֶד (*hesed*) — keep the range

248 occurrences in the Hebrew OT (`word H2617A`). The tool's lexicon gloss is "kindness"; its in-verse gloss at Exod.34.6 is "covenant loyalty"; in LXX verses ἔλεος co-occurs with it 202 times (`word ἔλεος`). The range: loyal love, kindness, faithfulness within a relationship, mercy. Pick the sense from context and say so; don't load all of them into one verse (totality transfer). A homonym חֶסֶד means "disgrace" (Lev.20.17, tagged H2617B "shame").

## 8. Ketiv / Qere

Where the Masoretes' margin (Qere, "to be read") differs from the written consonants (Ketiv), the default WLC witness prints the Qere-based text; `--witness Ketiv` prints the written form.

> [HEB Ps.100.3] הוּא־עָשָׂנוּ וְלוֹ אֲנַחְנוּ
> Literal: he made-us and-his we
> Natural: he made us, and we are his

> [HEB:Ketiv Ps.100.3] הוּא־עָשָׂנוּ וְלֹא אֲנַחְנוּ
> Literal: he made-us and-not we
> Natural: he made us, and not we ourselves

Show both when the difference affects meaning.

## 9. LXX and DSS alongside the MT

Run `lookup.py lxx <ref>` and `dss <ref>` on key OT verses. Report differences as witnesses, not corrections: Isa.53.11 (1QIsaa and LXX add "light"), Isa.7.14 (עַלְמָה / παρθένος), Isa.9.6 (LXX μεγάλης βουλῆς ἄγγελος for the names), Deut.6.4 (LXX adds a sentence before ἄκουε Ισραηλ). Quote each in its own tag.

## Commands used

```
lookup.py verse Gen.1.1 | Gen.1.2 | Gen.1.3 | Gen.1.26 | Gen.2.24 | Gen.3.16 | Gen.11.3 | Exod.3.14 | Exod.34.6 | Isa.9.6 | Isa.7.14 | Ps.19.1 | Ps.82.6 | 1Sam.28.13 | Lev.20.17
lookup.py verse Ps.100.3 ; verse Ps.100.3 --witness Ketiv
lookup.py word חֶסֶד ; word H2617A ; word ἔλεος ; word אֱלֹהִים
lookup.py lxx Isa.53.11 | Isa.7.14 | Isa.9.6 | Deut.6.4 ; dss Isa.53.11
```
