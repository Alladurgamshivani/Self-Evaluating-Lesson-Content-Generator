# Step-by-step guide: from this ZIP to a finished submission

Total time: about 3 to 4 hours of work plus recording. Do the steps in order.

---

## PART A: Set up and understand (45 min)

### Step 1. Unzip and open the project
Unzip `genai-lesson-agent.zip`, open the folder in VS Code (or Cursor).
Open a terminal in that folder.

### Step 2. Create a virtual environment and install
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
You need Python 3.10 or newer (`python --version`).

### Step 3. Run the offline test and the mock demo
```bash
python -m unittest discover -s tests -v    # expect: 19 tests OK
python main.py --mock                      # watch the loop: fail, fail, pass
python main.py --eval-suite --mock         # evaluator catches every bad lesson
```
Open `outputs/mock_run/rejection_log.md` to see what the log looks like.
The mock model is a simulation. It proves the plumbing works. It does NOT prove lesson quality.

### Step 4. Read the code in this order (you must be able to explain it on camera)
1. `src/rubric.py` the 8 checkpoints (the heart of the project)
2. `src/checks.py` the code checks
3. `src/evaluator.py` how code + LLM verdicts are merged, why it fails closed
4. `src/graph.py` the loop and `route_after_evaluate`
5. `src/generator.py` and `prompts/generator_v1.md`
6. `src/memory.py` and `src/refiner.py` memory and self-evolving
7. `docs/architecture.md` the reasoning behind every choice

---

## PART B: Connect a real model (20 min)

### Step 5. Get a free API key
Pick one. Free tiers change, so check the provider's page.
- **Gemini**: Google AI Studio -> "Get API key"
- **Groq**: console.groq.com -> API Keys (fast, generous free tier)

### Step 6. Configure `.env`
```bash
cp .env.example .env               # Windows: copy .env.example .env
```
Edit `.env`. Example using Gemini to write and Groq to judge (two different models = less bias):
```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
EVAL_PROVIDER=groq
GROQ_API_KEY=your_other_key_here
```
Model names change over time. If you see "model not found", look up the current model name in the
provider's docs and set `LLM_MODEL=` / `EVAL_MODEL=` in `.env`.

### Step 7. First real run
```bash
python main.py --topic "Introduction to RAG"
```
Watch the console. It prints each attempt, which checks failed and what changed.

---

## PART C: Tune it (60 to 90 min). This is where you show judgment.

### Step 8. Read the first real lesson and judge it yourself
Open `outputs/final_lesson.md`. Ask: would a 12th-grade student from a Telugu-medium school understand this?
Check every fact against `prompts/reference_notes.md`. If the system passed a lesson you think is bad,
that is a finding: write it down, then fix the rubric or prompt (and bump `RUBRIC_VERSION`).

### Step 9. Run `--eval-suite` with the REAL evaluator
```bash
python main.py --eval-suite
```
Every broken lesson must be caught, and the control must pass. If the real model misses the wrong-fact case,
strengthen `prompts/evaluator_v1.md` (for example, add "quote the exact words") or switch the evaluator model.
This is a great story for your video: "my first evaluator missed X, so I changed Y".

### Step 10. Let memory and self-evolving work
Run the system 3 to 4 times, ideally on different topics:
```bash
python main.py --topic "Introduction to RAG"
python main.py --topic "What are Embeddings?"
python main.py --show-memory
```
For a new topic, first edit `prompts/reference_notes.md` and the `JARGON_TERMS` list in `src/checks.py`.
After a check fails twice, a new rule appears in `memory/lessons_learned.json`
and a reason is added to `memory/prompt_changelog.md`. The next run loads it.
Note the number of attempts before and after the rule. Show that in the video.

### Step 11. Optional bonus: vernacular glossary
```bash
python main.py --glossary Telugu
```
This matches NxtWave's mission (learning in the mother tongue). It is added after the lesson passes,
so it is not judged by the rubric. Say so in the video, and have a native speaker check it.

### Step 12. Final clean run for submission
```bash
python main.py --reset-memory      # optional: clean slate so the log tells a clear story
python main.py --topic "Introduction to RAG"
```
Commit the resulting `outputs/final_lesson.md` and `outputs/rejection_log.md`.
If the status is `NEEDS_HUMAN_REVIEW`, read the log, fix the cause, and run again.

---

## PART D: The three deliverables (60 min + recording)

### Step 13. GitHub repo
```bash
git init
git add .
git commit -m "Self-evaluating lesson generator"
git branch -M main
git remote add origin https://github.com/<you>/genai-lesson-agent.git
git push -u origin main
```
Check: `.env` is NOT in the repo (it is in `.gitignore`). Never push an API key.
The README already has setup and run instructions and the architecture diagram.

### Step 14. Document (Google Doc or Notion)
Follow `docs/submission_document_outline.md`. Paste the final lesson, then an appendix with the rubric table,
a rejection-log excerpt and design decisions. Set sharing to "anyone with the link can view".

### Step 15. Loom video (15 to 20 minutes, face visible)
Follow `docs/video_script.md`. Turn your camera on in Loom. Do one practice take first.
Required by the brief: (1) workflow running end to end, (2) evaluator catching a deliberate error,
(3) face-visible walkthrough of how it works.

### Step 16. Submit the form
https://forms.gle/GKMb6wa7HiGFrXvC6 with: GitHub link, Doc link, Loom link.
Open each link in a private browser window first to confirm access.

---

## Submission checklist

- [ ] `python -m unittest discover -s tests` passes
- [ ] Real run finished with status PASSED (or honestly explained if not)
- [ ] `outputs/final_lesson.md` and `outputs/rejection_log.md` committed
- [ ] `--eval-suite` run with the real evaluator, result noted
- [ ] Memory shows at least one learned rule and a before/after comparison
- [ ] No API keys in the repo
- [ ] Google Doc / Notion link opens without login
- [ ] Loom: face visible, 15 to 20 minutes, link opens without login
- [ ] You can explain every file on camera

## Troubleshooting

| Problem | Fix |
|---|---|
| `GEMINI_API_KEY is not set` | Check `.env` exists in the project root and has no spaces around `=` |
| `HTTP 429` | Free-tier rate limit. The client waits and retries; if it keeps failing wait a minute or use another provider |
| `HTTP 404 model not found` | Set `LLM_MODEL` / `EVAL_MODEL` to a current model name from the provider docs |
| Evaluator says everything passes | Run `--eval-suite`, strengthen `prompts/evaluator_v1.md`, use a different evaluator model |
| Lesson keeps failing C4 | Lower sentence length in the generator prompt; check the reason text for the exact long sentence |
| Lesson keeps failing C3 | The heuristic wants "X is / means / called" in the same sentence as the first use of the term |
| `NEEDS_HUMAN_REVIEW` | Expected when retries run out. Read the log, fix the cause, run again |
| Windows `source` not found | Use `.venv\Scripts\activate` |
