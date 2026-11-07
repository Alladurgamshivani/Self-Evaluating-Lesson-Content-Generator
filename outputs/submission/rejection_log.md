# Rejection log: Introduction to RAG

- Run: `20261107-112546`  |  Generated: 2026-11-07 11:26
- Rubric version: 1.2  |  Max retries: 2
- Final status: **PASSED**
- LLM calls: 4  |  Prompt tokens: 8705  |  Completion tokens: 5343

## Attempt 1: FAILED (6/8 checks)

| Check | Result | Judged by | Reason |
|---|---|---|---|
| C1 Covers the key points | PASS | llm | Includes clear What, Why, and How sections with real content. |
| C2 Accurate and grounded | **FAIL** | llm | [llm] Invented specific fact "minimum GPA is 7.5" (and "Turmeric – ₹120 per kg") not supported by notes. |
| C3 No unexplained jargon, simple words | PASS | code+llm | OK |
| C4 Short, easy sentences | PASS | code | Average sentence length is 11.1 words; long sentences are 0%. |
| C5 Teaches by example | **FAIL** | llm | [llm] Lesson lacks a simple analogy to illustrate RAG. |
| C6 Coherent teaching flow | PASS | code+llm | OK |
| C7 Recap and self-check | PASS | code | Recap has 5 points and Check Yourself has 3 questions. |
| C8 Right length | PASS | code | Length is 642 words. |

Metrics: 642 words, 11.1 avg words/sentence.

**What changed on retry:** Changes made after failing: C2, C5. Removed or replaced: # Getting Started with Retrieval‑Augmented Generation | A student asks a chatbot about the date of the next university exam. The chatbot answers, but the date is wrong because its knowledge stopped last year. Added or updated: # Introduction to Retrieval‑Augmented Generation | A student asks a chatbot for the date of the next exam, but the answer is old and wrong.

**Did the retry fix it?**
- C2 Accurate and grounded: FAIL -> PASS
- C5 Teaches by example: FAIL -> PASS
- Words: 642 -> 644; average sentence: 11.1 -> 11.5

## Attempt 2: PASSED (8/8 checks)

| Check | Result | Judged by | Reason |
|---|---|---|---|
| C1 Covers the key points | PASS | llm | Lesson clearly explains what RAG is, why it matters, and how it works. |
| C2 Accurate and grounded | PASS | llm | All factual statements match the reference notes; no unsupported claims. |
| C3 No unexplained jargon, simple words | PASS | code+llm | OK |
| C4 Short, easy sentences | PASS | code | Average sentence length is 11.5 words; long sentences are 2%. |
| C5 Teaches by example | PASS | llm | Provides two concrete Indian examples and a clear analogy. |
| C6 Coherent teaching flow | PASS | code+llm | OK |
| C7 Recap and self-check | PASS | code | Recap has 5 points and Check Yourself has 3 questions. |
| C8 Right length | PASS | code | Length is 644 words. |

Metrics: 644 words, 11.5 avg words/sentence.
