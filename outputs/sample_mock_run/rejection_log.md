# Rejection log: Introduction to RAG (Retrieval-Augmented Generation)

- Run: `20261106-110143`  |  Generated: 2026-11-06 11:01
- Rubric version: 1.0  |  Max retries: 2
- Final status: **PASSED**
- LLM calls: 8  |  Prompt tokens: 0  |  Completion tokens: 0

## Attempt 1: FAILED (2/8 checks)

| Check | Result | Judged by | Reason |
|---|---|---|---|
| C1 Covers the key points | PASS | llm | what/why/how all present |
| C2 Accurate and grounded | **FAIL** | llm | [llm] The lesson says the model is retrained on documents, but note R3 says RAG does not change the model. |
| C3 No unexplained jargon, simple words | PASS | code+llm | OK |
| C4 Short, easy sentences | **FAIL** | code | [code] average sentence length is 28.4 words (limit 15); 3 of 5 sentences are over 25 words (limit 10%), e.g. "Today we study RAG, which uses an LLM together with embeddings and a vector database to gi...". |
| C5 Teaches by example | **FAIL** | llm | [llm] Fewer than two concrete examples were found. |
| C6 Coherent teaching flow | **FAIL** | code+llm | [code] Missing or out-of-order section(s): 'Example', 'Check Yourself'. |
| C7 Recap and self-check | **FAIL** | code | [code] Recap has only 1 point(s), needs at least 3; there is no check yourself section. |
| C8 Right length | **FAIL** | code | [code] Lesson is too short: 142 words (minimum 500). |

Metrics: 142 words, 28.4 avg words/sentence.

**What changed on retry:** (mock) Rewrote the lesson to fix: C2, C4, C5, C6, C7, C8.

## Attempt 2: FAILED (6/8 checks)

| Check | Result | Judged by | Reason |
|---|---|---|---|
| C1 Covers the key points | PASS | llm | what/why/how all present |
| C2 Accurate and grounded | PASS | llm | No claim contradicts the notes. |
| C3 No unexplained jargon, simple words | PASS | code+llm | OK |
| C4 Short, easy sentences | PASS | code | Average sentence length is 7.9 words; long sentences are 0%. |
| C5 Teaches by example | PASS | llm | Two or more examples found. |
| C6 Coherent teaching flow | **FAIL** | code+llm | [code] Missing or out-of-order section(s): 'Check Yourself'. |
| C7 Recap and self-check | **FAIL** | code | [code] There is no check yourself section. |
| C8 Right length | PASS | code | Length is 801 words. |

Metrics: 801 words, 7.9 avg words/sentence.

**What changed on retry:** (mock) Rewrote the lesson to fix: C6, C7.

## Attempt 3: PASSED (8/8 checks)

| Check | Result | Judged by | Reason |
|---|---|---|---|
| C1 Covers the key points | PASS | llm | what/why/how all present |
| C2 Accurate and grounded | PASS | llm | No claim contradicts the notes. |
| C3 No unexplained jargon, simple words | PASS | code+llm | OK |
| C4 Short, easy sentences | PASS | code | Average sentence length is 7.9 words; long sentences are 0%. |
| C5 Teaches by example | PASS | llm | Two or more examples found. |
| C6 Coherent teaching flow | PASS | code+llm | OK |
| C7 Recap and self-check | PASS | code | Recap has 6 points and Check Yourself has 3 questions. |
| C8 Right length | PASS | code | Length is 834 words. |

Metrics: 834 words, 7.9 avg words/sentence.
