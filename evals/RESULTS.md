# Eval results — original-text-sermons, iteration 1

Graded 2026-11-19 against `evals/evals.json` (12 evals, 63 assertions). Per-run detail is in `evals/runs/iteration-1/<name>/grading.json`.

How it was graded: `evals/grade_programmatic.py` on every run (all 13 sermon files: check_sermon exit 0, 0 errors, 0 warnings). Every count, morphology tag and witness claim that an assertion depends on was re-checked with `scripts/lookup.py`. For the chat-only answers (evals 7 and 12), the quote blocks were put into a scratch file and run through `check_sermon.py`; no quote or tag errors came back. Template headings, frontmatter and the copied-sentence check were done with grep and diff.

## Summary

| # | eval | passed / total | result |
|---|---|---|---|
| 1 | quote-fidelity-romans-es | 4/4 | PASS |
| 2 | tradition-traps-matt16-acts2-en | 5/5 | PASS |
| 3 | contested-readings-john1-gal2-gen1 | 5/5 | PASS |
| 4 | text-criticism-comma-mark16-john8 | 5/6 | FAIL |
| 5 | fallacies-dynamis-aorist-en | 6/6 | PASS |
| 6 | lxx-usage-phil2-isa45-en | 6/6 | PASS |
| 7 | dss-isa53-11-light-en | 6/6 | PASS |
| 8 | audience-non-christian-evangelistic-es | 4/5 | FAIL |
| 9 | template-default-and-custom-skeleton-en | 4/4 | PASS |
| 10 | languages-same-passage-es-and-en | 5/5 | PASS |
| 11 | intake-bare-request-es | 5/5 | PASS |
| 12 | usage-ekklesia-word-study-en | 5/6 | FAIL |
| | **overall** | **60/63 (95.2%)** | **9/12 evals fully pass** |

## Failed assertions

### Eval 4: text-criticism-comma-mark16-john8
**Failed assertion:** "The transcript shows lookup.py `variants` (or `verse`) was run covering each of the three passages; for John 7:53-8:11 … split calls (John.7.53 and John.8.1-11) or per-verse calls count."

**Evidence:** The run covered Mark 16:9–20 (`variants Mark.16.9-20`) and 1 John 5:7–8. For John it ran only `verse/variants John.7.53`, `verse/variants John.8.11` and `verse John.8.1|2|3|7|10`. It never ran `variants John.8.1-11`, and it made no call at all for 8.4, 8.5, 8.6, 8.8 or 8.9. This shows in the handout:
- "THGNT has 8:1–10" is a guess based on five verses.
- The only wording difference it reports inside the story is the one in 8:11.

The data has much larger differences. The grader ran `variants John.8.1-11` and got 207 tokens on which the editions don't all agree. For example, SBL 8.9 adds "καὶ ὑπὸ τῆς συνειδήσεως ἐλεγχόμενοι", which THGNT lacks.

### Eval 8: audience-non-christian-evangelistic-es
**Failed assertion:** "The sermon gives who/where/when context for the passage in one or two sentences before reading the text."

**Evidence:** The context paragraph gives *who* (Juan, Jesús de Nazaret, Nicodemo) and *when* (siglo primero, de noche), but it never names *where* the scene takes place (Jerusalem). It is also five sentences long, not one or two. This is a narrow miss that comes from reading the rule strictly. A looser grader could accept "de Nazaret" or "judío" as the place (see the analyst notes).

### Eval 12: usage-ekklesia-word-study-en
**Failed assertion:** "The response draws no conclusion that goes beyond the cited examples (it states what the examples show and says what they do not show)."

**Evidence:** The evidence gathering is excellent, but the summary goes past it:
- "The word itself never meant 'the called-out ones'" makes a claim about every use, based on about 10 sampled uses out of 265.
- "Greek cities used it for their citizens' meeting" rests on one city (Acts 19) plus a paraphrase of the noisy papyri entry.
- "'Church' also brings later associations … that 1st-century hearers of ἐκκλησία didn't have" and "Those who first used the word this way already had both meanings in their ears" are claims about what hearers thought, with no data behind them.

The response does state its limits for Philo and the papyri, but these sentences are not held to the evidence.

## Analyst notes

### Assertions that don't tell good runs from bad ones
- **"Passes check_sermon.py with 0 errors"** appears in 9 evals. The skill tells the executor to loop until the validator exits 0, and it did every time (13/13 files, 0 warnings). This works as a regression gate, but it never separates good runs from bad ones. The meaningful checks are the content assertions next to it.
- **Frontmatter echo checks** pass for any run that copies the prompt: eval 1 #4 (language/audience), eval 8 #1 and eval 10 #1. The validator already rejects malformed frontmatter.
- **Partial quotes satisfy "shows the text."** Eval 6 #1 passed with Isa 45:21 quoted only from its second half. If the user asks to "see what the texts actually say", the assertion should require full verses or an explicit ellipsis.
- **The neutrality assertion is too easy to pass.** Eval 7 #5 passed a response that says "the older witnesses lean towards 'light'" and calls the scrolls and the LXX "two independent kinds of witness". Neither statement is in the data. Tighten it to: no weighting words (lean, favor, independent, more reliable) unless the data backs them.
- There is no baseline (without-skill) run, so how well each assertion separates good from bad runs is judged by inspection, not measured. The most discriminating assertions are eval 2 #1–3, eval 5 #6, eval 6 #2–5, eval 7 #3–4, eval 10 #4 and eval 12 #6.

### Gaps no assertion covers (seen in this iteration)
- **Accurate, complete reporting of each witness.** In eval 7 the response says 1Q8 "is broken" after אור. The data shows the fragment continues and reads עבדי ("my servant"), agreeing with the MT, as 4Q58 does. Only 1QIsaa's עבדו ("his servant") was reported. This is selective reporting that tilts slightly toward one side, and no assertion caught it.
- **Interior variants in long passages** (eval 4, John 8:4 and 8:9).
- **`passage:` frontmatter in studies with several texts** records only the first ref (evals 2, 3, 4).
- **Proposing passages for a topic-only request** (SKILL step 2). Eval 11 did it, but nothing checks it.

### Patterns across failures and notes
1. **Staying inside the evidence is the weak spot.** All three failures are about the edge of the evidence: incomplete coverage (eval 4), a reference rule only partly applied (eval 8), and conclusions wider than the data (eval 12). The same pattern shows up below the assertion level:
   - Weighting language in eval 7.
   - Background claims presented as fact that no lookup produced: Philo's date and "probar un metal" (eval 1); "manuscripts of this period have no capital letters" (eval 2), which is wrong as worded since early manuscripts are all capitals; the correct point is that they have no case distinction; "Paul's hymn" and "the LXX his readers held" (eval 6); "Josephus wrote in the same generation" (eval 12).
2. **Ask-then-proceed intake.** Evals 3, 5 and 6 ask the template question and then draft with the default anyway. That is harmless in one-shot evals, but it doesn't follow either intake path cleanly.
3. **Doctrinal leans (notes only, both mild):**
   - Eval 8 presents a self-chosen-judgment reading of John 3:18–19 as what the text says ("No es que Dios esté esperando para caer encima…").
   - Eval 5 says "a report about God, not about us".
   - No tradition vocabulary appeared on any Literal or Natural line in any run. Every Greek and Hebrew quote that was checked matches `lookup.py`, and Acts 8:1 and 8:3 in eval 12 come from the `usage` sample contexts. No quote from memory was found.
4. **Invented first-person anecdote.** Eval 9's custom opener tells a story as the preacher's own experience ("the thing my son said at dinner").

### The changes most likely to fix the failures (priority order)
1. **Coverage rule for long passages** (SKILL.md step 3 and `references/text-criticism.md`): run `variants` (NT) or `dss` + `lxx` (OT) on the *whole* passage. Split at chapter boundaries (`John.7.53` + `John.8.1-11`) and never sample verses. Report interior variants that change meaning. Optionally have `lookup.py` accept ranges that cross chapters and split them itself. **Fixes eval 4.**
2. **Keep conclusions within the evidence** (hard rule 14, `exegetical-fallacies.md` §1, and the word-study path in SKILL.md):
   - Word-study summaries must be scoped to the evidence ("in the N examples shown…").
   - No universal claims (never, always, all hearers), and no claims about what hearers thought.
   - No weighting words at contested readings (lean, independent, more reliable) unless the data shows it.
   - Reword the root-fallacy "Right" line so its model is the bounded "'Called out' is not in the usage", not "never meant".

   **Fixes eval 12 and the eval 7 tilt.**
3. **Make the context sentence explicit for non-christian audiences** (`references/audiences.md`, and the Text and Hook guidance in `templates/big-idea.md` and `hook-book-look-took.md`):
   - Require one or two sentences that name *who* (writer or speaker), *where* (the place of the scene) and *when*.
   - Add an example line, e.g. "In Jerusalem, in the first century, a teacher named Nicodemus comes to Jesus at night."

   **Fixes eval 8.**

Secondary changes:
- In SKILL.md step 1, say what to do in one-shot requests when only the template is missing ("use the default and say so; don't ask"). This removes ask-then-proceed.
- Add to rule 14 that background facts (dates, scholarly labels such as "hymn") must be marked as background or left out.
- Add a line forbidding invented first-person anecdotes; offer illustrations framed as hypothetical instead.

## Overall pass rate

**60/63 assertions (95.2%). 9 of 12 evals pass fully.** The three failures (evals 4, 8, 12) share one root cause: the evidence was gathered or used only partly. None of them comes from a fidelity, quoting or tradition-vocabulary error.

---

# Iteration 2

Graded 2026-11-19. Five evals were re-run in `evals/runs/iteration-2/` after commits 6f69c2a and 8c1a028. Those commits changed SKILL.md, the references, `lookup.py` and `check_sermon.py`. The changes were:
- the κύριος rule
- full-passage coverage
- keeping conclusions within the evidence
- the required setting sentence
- a ban on invented anecdotes

`evals/evals.json` is unchanged, so the assertions are the same as in iteration 1.

How it was graded:
- `grade_programmatic.py` on all 5 sermon files: check_sermon exit 0, 0 errors, 0 warnings.
- Every edition list, count and context an assertion depends on was re-checked with `lookup.py`. This covered Mark 16 and John 8 variants, the Isa 45 LXX/WLC divine names, `usage κύριος`, `usage ἐκκλησία` (now split by witness: Josephus 48, Philo 23), John 2:23, and Josephus Ant.16.62 and War.4.162.
- The 10 chat quote blocks in eval 12 were run through `check_sermon.py --quotes-only --lang en`: exit 0.

Per-run detail: `evals/runs/iteration-2/<name>/grading.json`.

## Summary

| # | eval | iteration 1 | iteration 2 | change |
|---|---|---|---|---|
| 4 | text-criticism-comma-mark16-john8 | 5/6 FAIL | 6/6 PASS | +1 |
| 6 | lxx-usage-phil2-isa45-en | 6/6 PASS | 6/6 PASS | = |
| 8 | audience-non-christian-evangelistic-es | 4/5 FAIL | 5/5 PASS | +1 |
| 9 | template-default-and-custom-skeleton-en | 4/4 PASS | 4/4 PASS | = |
| 12 | usage-ekklesia-word-study-en | 5/6 FAIL | 6/6 PASS | +1 |
| | **iteration-2 subset** | **24/27 (88.9%)** | **27/27 (100%)** | +3 |

**Failed assertions in iteration 2:** none.

## Comparison with iteration 1

- **Eval 4 (coverage).** The run now calls `variants John.7.53` and `variants John.8.1-11` (207 rows) and `variants Mark.16.9-20`, plus per-edition `verse` calls for every verse of both passages. The handout reports the wording differences inside the passages, each with its edition list:
  - John 8:9, the conscience clause: TR+Byz and the SBL text.
  - John 8:10 additions: TR+Byz.
  - Mark 16:18 "with their hands": NA28/THGNT/WH.
  - Mark 16:17 καιναῖς and 16:19 Ἰησοῦς.

  It explains the effect on translations (BSB vs KJV). It also corrects the bracket report: ]] after Mark 16:20 appears in THGNT/Byz/TR. All of this was verified against the data.
- **Eval 8 (setting sentence).** "En Jerusalén, en el siglo primero, durante la fiesta de la Pascua judía, un maestro respetado llamado Nicodemo va a ver a Jesús de noche" is two sentences, and the place comes from `verse John.2.23`. "vida eterna" is now explained in the same sentence.
- **Eval 12 (keeping conclusions within the evidence).** The summary now names its contexts ("In the contexts shown here (LXX Deut 4:10 … Acts 19:39; the two inscriptions)"). It says "Nothing here tells us how every first-century hearer understood the word." The iteration-1 universals ("never meant", "hearers didn't have") are gone. The papyri are now limited to the inscriptions the entry cites.
- **Eval 6.** Still 6/6, and the iteration-1 notes are resolved: Isa 45:21 is quoted in full, and the "Paul's hymn" label is gone. The new κύριος rule is applied cleanly. The run uses the range from `usage κύριος` (address, owner, LXX for יהוה; 5,130 co-occurrences, verified) and gives options (a) title, (b) LXX word for the divine name, (c) both, with "the data does not decide".
- **Eval 9.** Still 4/4. The invented first-person opener is replaced by a hypothetical ("Imagine lying awake…"), and the Notes explain why.

## Regressions

No assertion regressed: 0 of 27 assertions went from pass to fail.

Notes that persist or are new (none caused a failure):
- **Eval 8, doctrinal lean (persists and is slightly extended).** One reading of John 3:18 is still given as what the text says: "el que no confía 'ya ha sido juzgado'. No porque Dios haya venido a condenarlo, sino porque ha rechazado la cuerda". A new gloss appears on 3:21, "no por su propio mérito", which the Greek doesn't state. The run does improve elsewhere: it now shows who speaks in 3:16–21 as an open question.
- **Eval 9, minor lean.** The sermon leaves "the Lord is near" open (Jesus / YHWH echo / both), but the Response then says "the God who is near", which quietly picks one option.
- **Eval 12, minor inference.** Acts 8:3 is glossed as "people who met in houses". The verse says Saul went house after house, so "met in houses" goes beyond it.
- **Risk of teaching to the test.** The updated references now contain near-verbatim model answers for the graded items:
  - the scoped ἐκκλησία summary ("In the 10 NT and LXX contexts…", `exegetical-fallacies.md`)
  - the full Isa 53:11 witness list (`text-criticism.md`)
  - "8:9 alone has 31 rows" for John 8

  The iteration-2 gains on evals 4 and 12 may partly reflect this. Add held-out evals before trusting the improvement:
  - a word study on a lemma the references don't use as an example (e.g. ἀπόστολος or πρεσβύτερος usage)
  - a different pericope that crosses a chapter boundary
  - a different DSS verse
- **Eval 7 was not re-run.** The iteration-1 tilt notes on it ("lean towards light", the 1Q8/4Q58 עבדי readings left out) are now covered by the reference text but not yet tested.

## Overall pass rate (combined)

The combined figure uses iteration-1 results for the 7 evals not re-run (1, 2, 3, 5, 7, 10, 11: 36/36) and iteration-2 results for the 5 re-run evals (27/27).

**63/63 assertions (100%). 12 of 12 evals pass fully** (iteration 1: 60/63, 95.2%, 9/12).

---

# Iteration 3

Graded 2026-11-19. All 15 evals in `evals/evals.json` were run in `evals/runs/iteration-3/`. Evals 13–15 are new. The only change to an existing assertion is eval 12 #5, which now asks for NT counts per edition.

The skill and validator changed substantially since iteration 2:
- TR and Byz verse text now comes from the printed editions (Scrivener TR, Robinson–Pierpont Byz).
- Untagged original-language text is an ERROR.
- `--quotes-only` mode exists for chat answers.
- New list-cap / separated-words WARN.
- NT counts are reported per edition.

How it was graded:
- `grade_programmatic.py` on all 13 sermon files: exit 0 and 0 errors for all of them. The remaining WARNs are 2 separated-words in the Psalm 23 sermon (eval 9), 1 each in the Psalm 1 pair (eval 10), and an accepted length WARN (eval 9, Philippians).
- Each chat-only answer (evals 7, 12, 13, 14, 15) was checked from everything above `## Tool log`, put in a scratch file and run through `check_sermon.py --quotes-only`. All exit 0.
- A grader script also flagged multi-word Greek or Hebrew runs that have no inline tag on the same line.
- Every data claim an assertion depends on was re-run against the current DB with `lookup.py`:
  - Acts 20:28 and 1 Tim 1:1 TR/Byz/SBL/THGNT text and variants
  - Rom 8:1 per witness and variants
  - counts for σάρξ, ἀγαπάω, μονογενής, ἐκκλησία, δύναμις, ἐφάπαξ, τελέω, κύριος, λογικός and φῶς
  - Mark 16 and John 7:53–8:11 brackets and interior variants under the new printed TR/Byz
  - `dss Isa.53.11`

Per-run detail: `evals/runs/iteration-3/<name>/grading.json`.

## Summary

| # | eval | it. 1 | it. 2 | it. 3 | result |
|---|---|---|---|---|---|
| 1 | quote-fidelity-romans-es | 4/4 | — | 4/4 | PASS |
| 2 | tradition-traps-matt16-acts2-en | 5/5 | — | 5/5 | PASS |
| 3 | contested-readings-john1-gal2-gen1 | 5/5 | — | 5/5 | PASS |
| 4 | text-criticism-comma-mark16-john8 | 5/6 | 6/6 | 6/6 | PASS |
| 5 | fallacies-dynamis-aorist-en | 6/6 | — | 6/6 | PASS |
| 6 | lxx-usage-phil2-isa45-en | 6/6 | 6/6 | 6/6 | PASS |
| 7 | dss-isa53-11-light-en | 6/6 | — | 6/6 | PASS |
| 8 | audience-non-christian-evangelistic-es | 4/5 | 5/5 | 5/5 | PASS |
| 9 | template-default-and-custom-skeleton-en | 4/4 | 4/4 | 4/4 | PASS |
| 10 | languages-same-passage-es-and-en | 5/5 | — | 5/5 | PASS |
| 11 | intake-bare-request-es | 5/5 | — | 5/5 | PASS |
| 12 | usage-ekklesia-word-study-en | 5/6 | 6/6 | 6/6* | PASS |
| 13 | tr-byz-quote-acts20-28-1tim1-1-order-es | — | — | 5/6 | FAIL |
| 14 | word-study-sarx-rom8-1-variant-notes-en | — | — | 5/6 | FAIL |
| 15 | chat-answer-es-quotes-only-john3-16 | — | — | 5/6 | FAIL |
| | **total** | 60/63 | (27/27 subset) | **78/81 (96.3%)** | **12/15 evals** |

\* Eval 12 #5 was revised for iteration 3 to ask for NT counts per edition. Evals 1–12 on their own score 63/63 (100%) in iteration 3. Evals 13–15 score 15/18 (83.3%).

## Failed assertions (iteration 3)

All three failures are the same issue: the new evals require an inline tag on every multi-word Greek run, but the skill and validator allow repeating text already quoted in a block above without one.

### Eval 13: tr-byz-quote-acts20-28-1tim1-1-order-es
**#5 fails** (the tagging clause only). The content part passes:
- It says the 1 Tim 1:1 `variants` order strings come from STEPBible TAGNT, and that κυριόυ is a data typo for the printed κυρίου.
- κυριόυ is never quoted as an edition's reading.
- `--quotes-only` exits 0.

The tagging part fails because two three-word runs outside any quote block have no inline tag:
- "(y Byz, dentro de su frase κυρίου καὶ θεοῦ)"
- "(c) κυρίου καὶ θεοῦ "del señor y Dios" — solo Byz"

### Eval 14: word-study-sarx-rom8-1-variant-notes-en
**#3 fails.** The variant phrase is tagged correctly as `[GRC:TR Rom.8.1]` / `[GRC:Byz Rom.8.1]`. Two other runs have no tag:
- "Paul himself uses κατὰ σάρκα for lineage:" (body)
- "it follows the dative τοῖς ἐν Χριστῷ Ἰησοῦ" (Notes)

### Eval 15: chat-answer-es-quotes-only-john3-16
**#4 fails.** Two runs have no inline tag:
- "el sujeto es ὁ θεὸς, "Dios""
- "en aposición: τὸν υἱὸν τὸν μονογενῆ, "al hijo, al único""

**Why the validator lets these through:** SKILL.md (Output format) says "Words already quoted verbatim in a quote block above need no new tag", and `check_sermon.py` implements that exemption. All three answers therefore pass `--quotes-only`. The assertions in evals 13–15 say "every" run and give no exemption. Every iteration-3 output relies on the exemption: the grader script counts 0–9 untagged repeated runs per file, and only eval 12 has none.

## Comparison with iterations 1 and 2

- **Evals 1–12 hold at 100%.** No assertion regressed from iteration 2 (evals 4, 6, 8, 9, 12) or from iteration 1 (the other seven).
- **Eval 4** works well with the new printed TR/Byz:
  - The iteration-2 caveat about [[ markers "inherited" by TR/Byz is no longer needed. In the data only NA/THGNT/WH open [[ at Mark 16:9, and only NA/THGNT/WH open it at John 7:53. The grader re-ran both.
  - All interior variants are reported with their edition lists (verified), and no manuscripts are claimed.
- **Eval 7** clears every iteration-1 note:
  - All four scrolls are reported, including the עבדי agreements in 1Q8 and 4Q58.
  - 4Q58 is quoted only up to the extant או.
  - No weighting words.
- **Eval 8** keeps the setting sentence ("En Jerusalén, en el siglo primero, durante la fiesta judía de la Pascua…"). The iteration-2 doctrinal glosses ("no por su propio mérito", "ha rechazado la cuerda") are gone.
- **Eval 12** names an edition for every NT count. Josephus 48 and Philo 23 are verified, and the evidence-scoping language is kept.

## Regressions (note level; no assertion regressed)

- **Eval 6.**
  - Isa 45:21 is again quoted only from הֲלוֹא / ἐγὼ ὁ θεός, although the chat says "All five Isaiah verses are quoted". Iteration 2 had the full verse.
  - κύριος switched to a capital "Lord" in prose and on the Natural line, while "God the father" stays lower case.
  - The close "when you say 'Jesus is Lord,' say it as Isaiah's tongue does" leans toward identifying the two referents, after the body declined to decide.
- **Eval 8.** "vida eterna" is now unexplained on the Natural line that non-christian hearers hear. Iterations 1 and 2 explained it in prose. The assertion is scoped to prose, so it still passes.
- **Evals 2 and 3 (recurring from iteration 1).** "Manuscripts of the first century had no capital letters" / "the Greek of this period had no capital letters". This is wrong as worded, since majuscule manuscripts are written entirely in capitals. SKILL.md and `fidelity-rules.md` correctly say "no case distinction"; the runners paraphrase it wrongly.

## Analyst notes

### Doctrinal leans (none tied to an assertion)
- **Eval 2.** The Big Idea, the Point 3 title ("How one enters") and the Conclusion present immersion as the way to enter the assembly, as the text's plain message. Meanwhile the body shows εἰς ἄφεσιν and ἐπὶ τῷ ὀνόματι with options. It also says "not … a building or an institution".
- **Eval 12.** A class discussion question moves from word usage to a church-practice conclusion: "what does that suggest about a group that never actually gathers? Let the texts … answer".
- **Eval 11.** Ephesians 2 is pitched as "el texto central" on grace. Romans 3:24 was left out because a nearby verse is contested; avoiding contested passages is not a skill rule.
- **Eval 1.** The theological overreach from the passive voice persists ("un cambio que no fabricamos, que recibimos").
- **Eval 3.** The Big Idea unifies all three texts with "God acts first", which is not a verdict but adds a theological frame.
- **Eval 15.** "Ninguno de esos contextos exige la idea de 'engendrar'" is scoped to the contexts shown, but it is mild weighting toward option (a).

### Other quality checks
- No tradition vocabulary appeared on any Literal or Natural line.
- No quote from memory was found: every quote and inline tag validated against the DB.
- Claims not backed by the tool log were limited to a few, mostly background:
  - Philo's century (eval 1)
  - "'Church' is a later church word" (eval 12)
  - the capital-letters phrasing (evals 2 and 3)

### SKILL.md ambiguities the runners hit
1. **Separated-words WARN handling.** Runners handled this WARN three different ways:
   - Some replaced Greek or Hebrew lemma lists in Notes with English glosses. That cleared the WARN but moved evidence out of the original language (eval 4: "Greek lemma lists replaced by glosses").
   - Some rewrote prose (evals 6, 7, 8, 13).
   - Some left the WARN in place (eval 9 Psalm 23: 2; eval 10: 1 each).

   SKILL.md doesn't say when a short lemma list in Notes is acceptable.
2. **Where an inline tag ends.** Runners hit this repeatedly:
   - Eval 1, run 2: "inline tag captured trailing ': ὑμῶν'".
   - Eval 13, run 2: "inline tag swallowed trailing κυριόυ".
   - Eval 9: "inline DSS tag preceded by `…`" was an ERROR.

   The rule doesn't say where the tagged text stops when Greek continues after punctuation.
3. **Settings carry-over.** Eval 9 copied the first sermon's audience and specialization to the second and said so. The skill doesn't say whether to carry settings over or ask.
4. **Big Idea fit for handouts and multi-passage requests.** Evals 2, 3, 4, 5 and 6 all used "one text per point" to fit three passages into the Big Idea template. Eval 4 is a text-criticism handout forced into Introduction/Big Idea/Point sections. The workaround is consistent but not written down anywhere.
5. **Capitalizing κύριος in plain prose.** The runs disagree:
   - eval 6: "Jesus the Anointed is Lord", capital
   - evals 9 and 10: "lord", lower case
   - eval 13: "del señor y Dios", a lower-case title next to a capitalized "Dios"

   The κύριος rule covers translation lines and predicates but not plain prose. The result looks inconsistent, and the casing can read as a signal about who is meant.

### Evals that don't tell good runs from bad ones
- Evals 1–12 now pass at 100%, so their remaining power to tell good from bad comes from the note-level checks above, not from the assertions.
- Evals 13–15 are discriminating, but their tagging clauses currently test the gap between the skill and the eval, not the quality of the run.

### Recommended fixes (priority order)
1. **Settle the tagging exemption.** Either remove "Words already quoted verbatim in a quote block above need no new tag" from SKILL.md and from `check_sermon.py` (at least in `--quotes-only` mode and in Notes), or add the same exemption to the assertions in evals 13 #5, 14 #3 and 15 #4. Removing it matches the intent of the new evals and the validator would then catch it. **Fixes all three failures.**
2. **Define where an inline tag ends, and when a lemma list is allowed.**
   - Inline tag: state that the tagged text ends at the first character that is not original-language text (or provide an explicit closing marker), and show an example with trailing punctuation.
   - Lemma lists: state when they are acceptable in Notes (e.g. at most N lemmas, each glossed), so runners stop moving evidence into English to silence the WARN.
3. **Write a rule for capitalizing κύριος in prose and on Natural lines.** Use one convention per language (e.g. lower-case "lord/señor" as a title unless grammar requires a name), state it in Notes, and apply it the same way to θεός/Dios in the same phrase.

   Also add one line warning against "no capital letters": the correct statement is "no upper/lower-case distinction".

Smaller fixes:
- Document "one text per point" and a handout variant for multi-passage requests.
- Set a default for carrying settings over between sermons in one request (reuse them and say so).
- Require full verses when the user asks to "see the text" (eval 6).

## Overall pass rate (iteration 3)

**78/81 assertions (96.3%). 12 of 15 evals pass fully.**
- Evals 1–12: 63/63 (100%), versus 60/63 in iteration 1 and 63/63 combined after iteration 2.
- Evals 13–15: 15/18. All three failures come from the same skill-versus-eval disagreement over tagging repeated Greek text.

---

# Iteration 4

Graded 2026-11-19. Evals 6, 13, 14 and 15 were re-run in `evals/runs/iteration-4/` after these fixes to SKILL.md, the references and the validator:
- **κύριος:** lower case by default, written "lord / Lord" at YHWH echoes and contested places, plus a Notes line explaining the convention.
- **Neutral closings:** rule 16, in both directions.
- **Tagging:** the exemption for verbatim repeats is now documented, and the end of an inline-tagged quote is defined.
- **Eval assertions:** evals 13–15 were revised so that a verbatim repeat (case and punctuation ignored) of an earlier quote counts as tagged.

How it was graded:
- `grade_programmatic.py` on the eval 6 sermon: exit 0, no errors or warnings.
- `check_sermon.py --quotes-only` on each chat answer (evals 13–15, everything above `## Tool log`): exit 0, no warnings.
- An independent scan for untagged multi-word Greek runs, applying the revised repeat rule.
- `lookup.py` re-checks of: the Isa 45 LXX/DSS readings, Rom 14:11, `usage ἐξομολογέομαι`, σάρξ domain tags in Rom 8:3–9 and Rom 1:3, Josephus Ant.6.120 and Ant.20.20, and the `usage ἀγαπάω` contexts.

## Summary

| # | eval | it. 3 | it. 4 | result |
|---|---|---|---|---|
| 6 | lxx-usage-phil2-isa45-en | 6/6 | 6/6 | PASS |
| 13 | tr-byz-quote-acts20-28-1tim1-1-order-es | 5/6 | 6/6 | PASS |
| 14 | word-study-sarx-rom8-1-variant-notes-en | 5/6 | 6/6 | PASS |
| 15 | chat-answer-es-quotes-only-john3-16 | 5/6 | 6/6 | PASS |
| | **iteration-4 subset** | 22/24 | **24/24 (100%)** | |

**Failed assertions:** none.

## Comparison with iteration 3

- **Evals 13–15 tagging.** All three now pass. Under the revised assertions, the iteration-3 answers would also have passed: the grader's scan of those answers with the new rule finds no untagged runs that aren't verbatim repeats. So this gain mainly comes from aligning the eval with the skill, not from a change in what the runners write.

  The runners did tighten up as well:
  - Eval 15 caught and tagged ὥστε … ἔδωκεν on its first validator run.
  - Eval 13's Notes now explain how κύριος and θεός are capitalized.
  - The iteration-3 weighting in eval 15 ("Ninguno de esos contextos exige…") is replaced by "los datos … no deciden por sí solos qué matiz quiso Juan".
- **Eval 6 fixes the iteration-3 note-level regressions:**
  - Isa 45:21 is quoted in full in Hebrew and Greek.
  - κύριος is written "lord / Lord" at Phil 2:11 and LXX Isa 45:25, with a convention line in Notes.
  - The leaning close ("say it as Isaiah's tongue does") is replaced by a neutral one ("let the evidence above, not a habit, shape your answer").
  - Point 3 now gives three options for κύριος, each with its basis.
- **Eval 13.** The κύριος/θεός asymmetry is fixed: Byz is rendered "del señor y dios / del Señor y Dios", with both words in the same form.

## Regressions

None, at assertion level or note level.

Minor notes:
- **Eval 6.** Rom 14:11 is quoted from ὅτι ἐμοὶ…, which leaves out the verse's own Ζῶ ἐγώ, λέγει κύριος. Those words bear on the κύριος question the sermon raises.
- **Eval 15.** It adds unmarked background names that the printed verses don't contain: "Naín", "Jairo", "el rey Monobazo".
- **Eval 13.** It contains the comma list "(Χριστοῦ, Θεοῦ, Κυρίου)": three separate words, each in the TR quote above. It was graded as a list of single words, not a phrase. The assertions should say how such lists are treated.

No doctrinal lean was found in either direction in the four runs.

## Overall pass rate (combined)

The combined figure uses iteration-3 results for the 11 evals not re-run (1–5 and 7–12: 57/57) and iteration-4 results for evals 6 and 13–15 (24/24).

**81/81 assertions (100%). 15 of 15 evals pass fully.**

Caveat: evals 1–12 now pass at 100%. Most of the remaining signal is in the note-level checks (leans, background claims, selective quoting), not in the assertions. Adding held-out evals (new lemmas, new contested passages) would test whether these results generalize.
