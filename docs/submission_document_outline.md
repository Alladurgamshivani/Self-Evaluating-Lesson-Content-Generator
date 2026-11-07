# Outline for your Google Doc / Notion submission

**Title:** Introduction to RAG: Beginner Lesson (generated and quality-checked by an agentic system)

## Part 1: The final lesson (clean formatting)
Paste `outputs/final_lesson.md` as it is. Use real headings (Heading 1 and 2), numbered lists and bold terms.
Put this first: the reviewers asked for "the final lesson content created".

## Part 2: Appendix: how this lesson was produced

1. **Run summary.** Topic, model(s) used for generator and evaluator, number of attempts, final status,
   LLM calls and tokens (copy the header of `rejection_log.md`).
2. **Rubric.** The 8-row table from the README (checkpoint, judged by code / LLM / both).
3. **Rejection log excerpt.** Paste attempt 1's failed checks with reasons, and "what changed on retry".
4. **Architecture.** The Mermaid diagram as an image (use mermaid.live to export) and 4 to 5 sentences.
5. **Design decisions.** One short paragraph each: LangGraph, hard pass/fail, hybrid evaluator,
   grounding notes, max 2 retries, memory and the rule that the refiner never edits the rubric.
6. **Evaluator test results.** The `--eval-suite` table. Add one honest line about anything it missed at first.
7. **Memory and self-evolving evidence.** One learned rule, why it was created, and attempts before vs after.
8. **Limitations and next steps.** Copy and personalise from the README.
9. **Links.** GitHub repo, Loom video.

Share setting: "Anyone with the link can view". Test it in a private window.
