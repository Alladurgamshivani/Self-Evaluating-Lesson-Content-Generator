# Loom video script (target 17 to 19 minutes, camera ON)

Speak naturally. Do not read this word for word. Know your numbers and your reasons.
Before recording: delete old outputs, run `--reset-memory`, close notifications, increase terminal font size.

| Time | Segment | What to show | What to say |
|---|---|---|---|
| 0:00 to 1:30 | Intro | Face + README title | Your name. "The brief is not to write a prompt. It is to build a system that generates a lesson, judges it, and decides by itself if it is good enough." |
| 1:30 to 4:30 | Architecture | `README` mermaid diagram | Walk the loop: load memory, generate, evaluate, retry or ship, update memory. Explain the 3 outcomes (pass, retry, flagged). |
| 4:30 to 7:30 | The rubric | `src/rubric.py` | 8 hard pass/fail checks. Why not scores. Why hybrid: 5 code checks, 5 LLM checks (C3 and C6 use both). Why grounding notes. Why fail closed. |
| 7:30 to 11:30 | Live run | Terminal: `python main.py` | Narrate each attempt: "C4 failed because the average sentence was 21 words, now it regenerates with that feedback." Open `rejection_log.md` and the final lesson. |
| 11:30 to 14:00 | Deliberate error | `python main.py --inject-error` then `--eval-suite` | "I planted: RAG works by retraining the model. Note R3 says the model is not changed. C2 fails with this exact reason. The retry fixes only that." Show the eval suite table: 5 broken lessons caught, 1 control passes. Mention any miss you found and how you fixed it. |
| 14:00 to 16:30 | Memory and self-evolving | `--show-memory`, `lessons_learned.json`, `prompt_changelog.md` | "After a check failed twice, the refiner wrote a rule. Run 1 needed N attempts, run 2 needed M." Explain why it can edit generator rules but never the rubric (Goodhart). |
| 16:30 to 18:30 | Trade-offs and limits | `docs/architecture.md` | Be honest: LLM judges can be lenient; jargon check is a heuristic; hand-written notes; short sentences can game C4. Cost: calls and tokens per run. |
| 18:30 to 19:00 | Next steps and close | Face | LangSmith/RAGAS, bigger eval set, human review queue, MCQs and code exercises through the same loop. |

## Tips
- Show a real failure and say what you learned. They value "curiosity about where things break".
- If the live run is slow, say "I sped this part up" and show the saved log instead of waiting silently.
- Keep your face visible in the Loom bubble the whole time.
- Practice the sentence "why max two retries": it caps cost, guarantees termination, and escalates to a human instead of failing silently.
