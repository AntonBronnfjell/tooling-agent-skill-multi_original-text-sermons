# Greek checks (NT and LXX)

Run these on every key word and clause before translating. Morphology codes are the tool's (`V-AAI-3S` = verb, aorist active indicative, 3rd sg.). Every example below was copied from `lookup.py` output; commands are listed at the end.

## 1. Aspect, not time-of-action

Greek tense-forms mark how the speaker views an action (whole vs in progress), not how it happened.

- **Aorist ≠ "once for all", ≠ instantaneous.** A 46-year building project is told with an aorist:

  > [GRC John.2.20] Τεσσεράκοντα καὶ ἓξ ἔτεσιν οἰκοδομήθη ὁ ναὸς οὗτος
  > Literal: forty and six years was-built the temple this
  > Natural: this temple took forty-six years to build

  Where the text means "once for all" it says so with a word — ἐφάπαξ:

  > [GRC Rom.6.10] τῇ ἁμαρτίᾳ ἀπέθανεν ἐφάπαξ
  > Literal: to-the sin he-died once-for-all
  > Natural: he died to sin once for all

- **Present ≠ always continuous.** The present views an action as ongoing *or* general/habitual *or* simply as a characteristic. ὁ πιστεύων (John.3.16, `V-PAP-NSM`) can be "the one who believes" (a description) without proving "keeps on believing". Where the sense of a present is debated, show it — e.g. 1John.3.9 ἁμαρτάνειν (`V-PAN`): the tool's gloss "to continue sinning" is an interpretation of the present, not the word itself; options: habitual "go on sinning" / plain "sin" with another explanation of the verse.
- **Perfect** (`R` in the code): a completed action with a resulting state — ἐγήγερται "has been raised (and is raised)" (1Cor.15.14).

## 2. Voice, including the middle

Active, passive, and **middle** (subject acts on/for itself, or has something done for itself). Many verbs are middle in form with active meaning (δύναται, `V-PNI-3S`, "is able").

> [GRC Acts.22.16] ἀναστὰς βάπτισαι καὶ ἀπόλουσαι τὰς ἁμαρτίας σου
> Literal: having-arisen be-immersed/washed (middle) and wash-away/get-washed-away the sins of-you
> Natural: get up, be immersed (or: washed) and have your sins washed away

Both imperatives are aorist **middle** (`V-AMM-2S`): permissive/causative ("let yourself be…") or reflexive ("…yourself"). Show the range; do not build doctrine on one sense of the voice.

## 3. The article — and Colwell (contested)

- The article marks identity, previous reference, or a class; its absence often makes a noun qualitative. English "a/the" do not map one-to-one.
- **Colwell's rule** observes that definite predicate nouns placed before the verb usually lack the article. It does **not** prove that an anarthrous pre-verbal predicate is definite. John.1.1c is the classic case:

  > [GRC John.1.1] καὶ θεὸς ἦν ὁ λόγος
  > Literal: and God/divine/a-god was the word
  > Natural: (options) "and the word was God" / "and what God was, the word was" / "and the word was a god"

  The subject is the arthrous ὁ λόγος; θεὸς is fronted and anarthrous. Show definite, qualitative and indefinite options with this basis (see `contested-readings.md`).
- **One article, two nouns joined by καί** (Titus.2.13, 2Pet.1.1): may present one referent or two — contested; show both.

## 4. Genitive categories

A genitive marks a relation; the kind of relation is the reader's call from context. Name the category when it matters:

- possessive, source, apposition, descriptive ("son of thunder" = thunderous), partitive;
- **subjective vs objective**: "the love of God" = God's love (subj.) or love for God (obj.).

> [GRC Gal.2.16] ἐκ πίστεως Χριστοῦ
> Literal: from faith/faithfulness of-Anointed
> Natural: (options) "by trust in the Anointed" / "by the Anointed's faithfulness"

*pistis Christou* (Gal.2.16, Rom.3.22) is contested; πίστις itself ranges over "trust" and "faithfulness". Present both readings.

## 5. Participles

Check tense (aspect relative to the main verb), and function: attributive, substantival ("the one who…"), or adverbial (time, means, manner, cause, condition, concession, purpose, attendant circumstance).

> [GRC Matt.28.19] πορευθέντες οὖν μαθητεύσατε πάντα τὰ ἔθνη
> Literal: having-gone therefore make-disciples all the nations
> Natural: so go and make disciples of all the nations

πορευθέντες is an aorist participle (`V-AOP-NPM`) before an aorist imperative: commonly attendant circumstance ("go and…"), carrying the imperative's force. "As you go" would need a present participle — don't preach a nuance the form doesn't have. βαπτίζοντες (present) after the main verb is usually manner/means.

## 6. Conditional sentences

| class | form | meaning | example |
|---|---|---|---|
| 1st | εἰ + indicative | assumed true *for the argument* — not "since" | 1Cor.15.14 εἰ δὲ Χριστὸς οὐκ ἐγήγερται |
| 2nd | εἰ + past indicative, ἄν in apodosis | contrary to fact | Luke.7.39 εἰ ἦν προφήτης, ἐγίνωσκεν ἂν |
| 3rd | ἐάν + subjunctive | possible / general | John.14.15 Ἐὰν ἀγαπᾶτέ με |

In 1Cor.15.14 the speaker does not believe the protasis; "since" would reverse the argument.

## 7. Word order and emphasis

Greek word order is free; fronted elements often carry emphasis or contrast (θεὸς in John.1.1c; Οὕτως in John.3.16). Note it, but don't over-read it: genre, rhythm and Semitic influence also move words.

## 8. Semitisms

NT and LXX Greek carry Hebrew/Aramaic idiom. Read them by Hebrew logic:

- "son(s) of X" = characterized by X: Υἱοὶ Βροντῆς "sons of thunder" (Mark.3.17).
- Cognate dative for intensity, like the Hebrew infinitive absolute (cf. Gen.3.16 הַרְבָּה אַרְבֶּה): Ἐπιθυμίᾳ ἐπεθύμησα "with desire I desired" = "I have eagerly desired" (Luke.22.15).
- καί chains, "and it happened", "answered and said", "before the face of".

## 9. The LXX as the lexicon of NT Greek

The LXX was the Greek scripture of most NT writers; its usage is the closest evidence for what a NT word meant to them. Use `lookup.py word <lemma>` (counts + Hebrew co-occurrence) and `usage <lemma>` (LXX, Josephus, Philo, papyri contexts). The Hebrew list is **same-verse co-occurrence, not alignment** — report it as such. From `word` output:

| Greek | NT | LXX | top Hebrew co-occurrence in LXX verses |
|---|---|---|---|
| ἐκκλησία | 117 | 77 | קָהָל 66 |
| πιστεύω | 245 | 48 | אָמַן 43 |
| ἔλεος | 27 | 239 | חֶסֶד 202 |
| κρίνω | 115 | 184 | שָׁפַט 105 |
| αἰώνιος | 71 | 115 | עוֹלָם 100 |
| ἀποστέλλω | 134 | 521 | שָׁלַח 456 |

Allusions: show both texts and the shared words; claim no more than the data shows. Phil.2.10–11 (πᾶν γόνυ κάμψῃ … πᾶσα γλῶσσα ἐξομολογήσηται) shares wording with LXX Isa.45.23 (κάμψει πᾶν γόνυ καὶ ἐξομολογήσεται πᾶσα γλῶσσα τῷ θεῷ). In that LXX passage (Rahlfs) the MT's יְהוָה stands in vv. 21, 24, 25, while the Greek has ὁ θεός in 21, no divine name in 24, and κυρίου in 25 — report exactly that, verse by verse.

## Commands used

```
lookup.py verse John.2.20 | Rom.6.10 | John.3.16 | 1John.3.9 | 1Cor.15.14 | Acts.22.16 | John.1.1 | Titus.2.13 | Gal.2.16 | Matt.28.19 | Luke.7.39 | John.14.15 | Mark.3.17 | Luke.22.15 | Phil.2.10 | Phil.2.11
lookup.py verse Gen.3.16 ; verse Isa.45.21|22|23|24|25 --corpus lxx ; verse Isa.45.21|24|25
lookup.py word ἐκκλησία | πιστεύω | ἔλεος | κρίνω | αἰώνιος | ἀποστέλλω
```
