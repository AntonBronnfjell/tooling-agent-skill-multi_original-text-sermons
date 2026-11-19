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
