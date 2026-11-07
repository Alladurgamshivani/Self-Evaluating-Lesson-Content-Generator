# Architecture and design decisions

Use this file as the base for the "design reasoning" part of your document and video.
The brief says: *we want to see how you build the system: your planning, a robust architecture, and the
reasoning behind your design choices.*

## 1. The problem in one sentence

Turn "ask an LLM for a lesson" into a **closed quality loop** that decides by itself whether content is good
enough to ship, explains every rejection, and gets better over time.

## 2. Components

| Component | File | Job |
|---|---|---|
| Generator | `generator.py` + `prompts/generator_v1.md` | Writes the lesson. On retry it also gets the old lesson, the failed checks, reasons and fix hints. |
| Evaluator | `evaluator.py`, `checks.py`, `rubric.py` | Hybrid judge. Returns strict PASS/FAIL per check with a reason. |
| Grounding notes | `prompts/reference_notes.md` | 18 verified facts. The evaluator's source of truth. |
| Orchestrator | `graph.py` | LangGraph state machine with a conditional loop and a hard retry limit. |
| Rejection log | `reporting.py` | What failed, why, what changed on retry. |
| Memory | `memory.py` | Run history, learned rules and a changelog, stored as JSON. |
| Refiner | `refiner.py` | Turns repeated failures into new generator rules (self-evolving). |
| Eval suite | `eval_suite.py` | Deliberately broken lessons that the evaluator must catch. |
| Mock model | `mock_llm.py` | Lets the whole system be tested offline. |

## 3. Decisions, alternatives and trade-offs

**Why LangGraph instead of n8n or a plain script?**
The flow is a graph with a conditional back-edge and shared state, which is exactly what LangGraph models.
Routing, state and retry logic are explicit and unit-testable (`route_after_evaluate`). n8n is faster for
visual integrations but harder to version-control, test and explain line by line, and awkward for custom
code checks. A plain `while` loop would work, so a fallback runner reuses the same node functions.
Trade-off: LangGraph adds a dependency and a learning curve.

**Why hard pass/fail instead of a 1-10 score?**
A score needs a threshold, and thresholds hide arguments ("is 7 good enough?"). Binary checks make the ship
decision unambiguous, make failures actionable ("C4 failed: average 22 words"), and are easier for an LLM
to judge consistently. Trade-off: no sense of "how close". The log shows how many checks passed instead.

**Why a hybrid evaluator (code + LLM)?**
Code is exact, free, repeatable and cannot be talked into passing. It handles sentence length, headings,
length, recap/quiz and the jargon-at-first-use heuristic (5 of 8 checks). The LLM is used only where meaning
is needed: truthfulness, whether examples are relatable, whether the flow builds. Trade-off: code checks are
proxies (short sentences do not guarantee clarity), so C3 and C6 need both halves to pass.

**Why grounding notes?**
Without a reference, "is it accurate?" is the model's opinion about the model's own output. With notes, the
evaluator checks the lesson against facts we verified. Trade-off: notes must be maintained by a human, and
they limit what the lesson can say.

**Why can the evaluator model differ from the generator?**
A model grading its own text tends to be lenient. `EVAL_PROVIDER` / `EVAL_MODEL` let you use another model;
evaluator temperature is fixed at 0 for repeatability. Trade-off: two models can mean two bills.

**Why fail closed?**
If the reviewer returns invalid JSON or skips a check, that check is marked FAIL. A confused evaluator must
never pass content by default.

**Why max 2 retries (hard cap 3)?**
It guarantees termination and bounds cost: at most 3 generations + 3 evaluations + 2 summaries per lesson.
If it still fails, the best attempt is shipped **flagged for human review** with the full log, never silently.
Trade-off: some lessons that a 4th try might fix get escalated to a human.

**Why "fix only what failed" on retry?**
Sending the previous lesson plus the failed checks and fix hints keeps what already passes and avoids
rewrites that fix one check and break another. The attempt-by-attempt metrics in the log show whether it worked.

**Why can the self-evolving step only add generator rules, never edit the rubric?**
If the system could rewrite its own exam it would drift toward easy passes (Goodhart's law). So: the refiner
may propose *generator* rules after a repeated failure (threshold = 2 new failures per check, up to 3 rules
per check, 12 total), every rule is logged in `memory/prompt_changelog.md`, rules mentioning the
rubric/evaluator are rejected, and rubric changes are a human decision with a version bump.

**Why JSON files for memory?**
Easy to inspect on camera, no setup, good enough for this scale. A vector store would be over-engineering
here. At production scale you would move to a database and retrieve only rules relevant to the topic.

**Why standard-library HTTP instead of an SDK?**
No install step for the LLM layer, one small file supports four providers, and it is easy to read.
Trade-off: no streaming, and you maintain retry logic yourself (exponential back-off on 429/5xx is included).

## 4. Failure modes considered

| What can go wrong | How it is handled |
|---|---|
| Reviewer returns broken JSON | One retry, then every LLM check fails closed |
| Reviewer is too lenient | Different model, temperature 0, code checks, `--eval-suite` regression test |
| Generator ignores feedback | Max retries, flagged output, log shows metrics per attempt |
| Infinite loop | Retry counter + routing function + hard cap of 3 + unit tests |
| Rate limits / network errors | Exponential back-off on 429/5xx, clear error message |
| Corrupted memory file | Backed up to `*.corrupt.json`, run continues with empty memory |
| Bad learned rule | Sanitised, length-limited, topic-neutral, logged, reversible (edit JSON) |
| Chatty model output ("Sure! Here is...") | `clean_output` strips fences and preambles |

## 5. Cost awareness

Every run records LLM calls and tokens (`usage` in the log and in `memory/run_history.json`).
Typical cost: 1 to 3 generations, 1 to 3 evaluations (one call each), up to 2 change summaries,
and at most a few refiner calls. Code checks cost nothing.

## 6. What I would do next

1. Add LangSmith tracing and RAGAS faithfulness scores as a second opinion on C2.
2. Grow the eval suite to 30+ labelled lessons (good and bad) and report precision and recall of the evaluator.
3. Add a human-review queue for flagged lessons and feed the human verdicts back into memory.
4. Reuse the loop for MCQs and coding exercises, running the code examples to catch broken syntax.
5. Topic-specific jargon lists generated from the reference notes.
