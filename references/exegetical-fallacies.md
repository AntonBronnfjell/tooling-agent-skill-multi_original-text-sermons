# Exegetical fallacies

Check every word study and every "the Greek really means…" sentence against this list. If a user prompt asks for one of these moves, decline the move and give the evidence-based reading instead. A word means what its users meant by it in context — established by usage (`lookup.py usage`, `word`, `search`), not by its parts, its history, or its English descendants. Every original-language example here was copied from `lookup.py` output.

## 1. Root fallacy

Meaning drawn from a word's components.

- **Wrong:** "ἐκκλησία is ἐκ + καλέω, so it means 'the called-out ones', a people separated from the world."
- **Right:** usage shows "assembly, gathering" — 77 times in the LXX (co-occurring with קָהָל, Israel's assembly, 66 times), in Josephus for Moses gathering the people (Ant.3.84 συγκαλεῖ τὸ πλῆθος εἰς ἐκκλησίαν), and in Acts.19.32 for a confused civic crowd in Ephesus (ἦν γὰρ ἡ ἐκκλησία συγκεχυμένη). "Called out" is not in any context the tool returned.

## 2. Etymological fallacy

Meaning drawn from an earlier stage of the word's history.

- **Wrong:** "πρεσβύτερος originally meant 'older man', so leaders called this must be old."
- **Right:** the tool lists two senses — G4245G "elder" (a role) and G4245H "old". Context decides which is in play.

## 3. Illegitimate totality transfer

Loading every sense a word can have into one occurrence.

- **Wrong:** "κόσμος in John.3.16 means the universe, the world system, humanity, adornment and the hostile order all at once." (`word κόσμος` lists 11 Louw–Nida domain codes.)
- **Right:** choose the sense the sentence needs — in John.3.16–17 the κόσμος is loved, can be judged and can be saved, so the human world is in view — and say why.

Same with חֶסֶד: pick "loyal love" *or* "kindness" for the verse; don't preach the whole lexicon entry.

## 4. Anachronism

Reading a later meaning (often an English descendant) back into the ancient word.

- **Wrong:** "δύναμις gives us 'dynamite' — the good news is God's explosive power" (Rom.1.16 δύναμις γὰρ θεοῦ ἐστιν εἰς σωτηρίαν).
- **Right:** dynamite was named in the 19th century; the influence runs from Greek to English, never back. In the LXX, δύναμις co-occurs most with חַיִל (strength, army, 147) and צָבָא (host, 134): capability, might, armies. Translate "power, ability, strength".

Also anachronistic: reading "church" buildings, "baptism" rites or later offices into 1st-century words — see `tradition-vocabulary.md`.

## 5. Word–concept fallacy

Treating a word and a concept as the same thing: assuming an idea is absent because its usual word is absent, or present because the word is.

- **Wrong:** "John.3.16 has no χάρις, so it says nothing about undeserved gift" — or "Trinity isn't in the text, so the text says nothing on the matter" (or the reverse: "the passage is about the Trinity because it names father, son and spirit").
- **Right:** describe what the passage itself says (ἔδωκεν "he gave"; the names it uses) and stop there. Absence of a later term is a fact about vocabulary, not a verdict.

## 6. Selective evidence

Citing only the occurrences that support the point.

- **Wrong:** "ἀγάπη/ἀγαπάω always means selfless divine love."
- **Right:** run `usage`/`search` and report the counter-cases: LXX 2Sam.13.15 uses ἀγάπη and ἠγάπησεν of Amnon's desire for Tamar, which turns to hatred; 2Tim.4.10 says Demas left ἀγαπήσας τὸν νῦν αἰῶνα, "having loved the present age". The word means "love"; its quality comes from context.

The mirror error is a conclusion wider than the examples — even a correct one.

- **Wrong:** "ἐκκλησία never meant 'the called-out ones'; everyone in the 1st century heard 'assembly'." (Built on ~10 sampled uses of 117 NT + 77 LXX; and no tool shows what hearers thought.)
- **Right:** "In the 10 NT and LXX contexts `usage ἐκκλησία` shows (Acts.5.11–9.31, Deut.4.10–23.2), the word names a gathering or a group of people; none shows 'called out'. These examples don't tell us how every hearer understood it."

## 7. Overspecification

Claiming more precision than the form or word carries.

- **Wrong:** "In John.21.15–17 ἀγαπᾷς (Jesus) vs φιλῶ (Peter) shows Peter can only offer a lesser love." Or: "the aorist means the action happened once for all."
- **Right:** the third question itself uses φιλεῖς (John.21.17), and both verbs share Louw–Nida domain 25 (love, affection); the alternation may be stylistic variation or a nuance — present both and don't build the sermon on it. For the aorist, see `linguistics-greek.md` §1 (John.2.20 — a 46-year building told in the aorist; Rom.6.10 — "once for all" comes from the word ἐφάπαξ).

## Quick check before writing

1. Is the meaning from usage in context, or from parts/history/English?
2. Did I pick one sense, with a reason?
3. Did I report counter-examples the tool returned?
4. Am I claiming precision the grammar doesn't give?

## Commands used

```
lookup.py word ἐκκλησία ; usage ἐκκλησία ; search ἐκκλησία --corpus ext ; verse Acts.19.32 ; verse Ant.3.84 --corpus ext --witness Josephus
lookup.py word πρεσβύτερος ; word κόσμος ; word δύναμις ; usage δύναμις ; verse Rom.1.16
lookup.py verse 2Sam.13.15 --corpus lxx ; verse 2Tim.4.10 ; verse John.21.15 ; verse John.21.17 ; word ἀγαπάω ; word φιλέω
lookup.py verse John.2.20 ; verse Rom.6.10
```
