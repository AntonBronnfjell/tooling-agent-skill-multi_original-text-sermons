---
name: big-idea
default: true
sections: Introduction, Text, Big Idea, Point 1, Point 2, Point 3, Conclusion, Notes
sections_es: Introducción, Texto, Idea central, Punto 1, Punto 2, Punto 3, Conclusión, Notas
suits: theology, teaching, pastoral, apologetics
---

# Template: Big Idea (expository, default)

One sentence from the text carries the whole sermon; three points unfold it in the passage's own order. Each `sections:` entry is a `##` heading in the sermon file, spelled exactly as listed; `sections_es:` gives the Spanish headings in the same order. Target: concise — ~1–2 pages, 500–1,300 words of body prose (quote blocks and Notes excluded), ~15–20 minutes spoken with the readings and pauses. File format: `templates/sermon-output.md`.

## Introduction

~10%. Raise the question the passage answers, in the audience's world. No original language yet. End by pointing to the text.

## Text

The passage in quote blocks, from `lookup.py verse` — one block per verse or clause, each followed by `Literal:` and `Natural:`. One or two sentences of setting (who, to whom, where in the book). Mention here any variant that changes the wording the audience knows.

## Big Idea

One sentence, in the target language, that the text itself states or directly implies — not a doctrine summary. Then two or three sentences: which words of the text carry it.

## Point 1

First movement of the passage. Quote the clause (quote block if it's a new line of text), make one linguistic observation that matters (aspect, voice, genitive, a word's usage from `lookup.py word/usage`), then apply. Apologetics: open with the objection this point answers.

## Point 2

Second movement, same pattern. If a contested reading falls here, show the options here (original, each reading, its basis, what context favors).

## Point 3

Third movement, same pattern. Comparison findings that change meaning for listeners belong in the point where they arise; the rest go to Notes.

## Conclusion

~10%. Restate the Big Idea in fresh words; one concrete response shaped by specialization and audience (evangelistic: a clear call to respond). End with the text's own words.

## Notes

Not preached. Bullets: variants (`text-criticism.md` format), contested readings with options (`contested-readings.md`), translation-comparison findings with class (`translation-comparison.md`), lookup commands used. Excluded from the spoken-length estimate.
