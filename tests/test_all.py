"""Run with:  python -m unittest discover -s tests -v     (no API key, no internet needed)

1. checks      : the deterministic checks behave as designed
2. evaluator   : the evaluator catches every deliberately broken lesson (and passes the good one)
3. workflow    : the loop terminates, logs rejections, saves outputs and memory, never exceeds max retries
4. llm wiring  : the real HTTP client works against a tiny local fake "OpenAI-compatible" server
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import checks, llm as llm_mod  # noqa: E402
from src.eval_suite import CASES, GOOD, inject_error, run_suite  # noqa: E402
from src.evaluator import _extract_json, evaluate  # noqa: E402
from src.graph import Context, build_app, new_run_id, route_after_evaluate  # noqa: E402
from src.memory import Memory  # noqa: E402
from src.mock_llm import MockLLM  # noqa: E402
from src.refiner import _sanitize  # noqa: E402

NOTES = (ROOT / "prompts" / "reference_notes.md").read_text(encoding="utf-8")
GEN_PROMPT = (ROOT / "prompts" / "generator_v1.md").read_text(encoding="utf-8")
EVAL_PROMPT = (ROOT / "prompts" / "evaluator_v1.md").read_text(encoding="utf-8")


def make_ctx(tmp, llm=None, gen_llm=None):
    llm = llm or MockLLM()
    return Context(gen_llm=gen_llm or llm, eval_llm=llm, memory=Memory(Path(tmp) / "mem"),
                   out_dir=Path(tmp) / "out", reference_notes=NOTES, generator_prompt=GEN_PROMPT,
                   evaluator_prompt=EVAL_PROMPT, say=lambda *_: None, mock=isinstance(llm, MockLLM))


class TestChecks(unittest.TestCase):
    def test_good_lesson_passes_all_code_checks(self):
        for fn in checks.CODE_CHECKS.values():
            ok, reason, _ = fn(GOOD)
            self.assertTrue(ok, f"{fn.__name__}: {reason}")

    def test_long_sentences_fail_readability(self):
        long = "This is a sentence that keeps going " * 6 + "."
        ok, _, m = checks.check_readability("## Hook\n\n" + long)
        self.assertFalse(ok)
        self.assertGreater(m["avg_words_per_sentence"], 15)

    def test_missing_section_detected(self):
        ok, reason, _ = checks.check_structure(GOOD.replace("## Why It Matters", "## Something Else"))
        self.assertFalse(ok)
        self.assertIn("Why It Matters", reason)

    def test_sections_out_of_order_detected(self):
        a, b = "## Recap", "## Check Yourself"
        swapped = GOOD.replace(a, "@@").replace(b, a).replace("@@", b)
        self.assertFalse(checks.check_structure(swapped)[0])

    def test_quiz_needs_three_questions(self):
        self.assertFalse(checks.check_recap_and_quiz(GOOD.replace("?", "."))[0])

    def test_length_limits(self):
        self.assertFalse(checks.check_length("## Hook\n\nToo short.")[0])
        self.assertFalse(checks.check_length("word " * 2000)[0])

    def test_jargon_must_be_explained_first(self):
        bad = GOOD.replace("## Hook\n\n", "## Hook\n\nWe use an LLM and a vector database here. ", 1)
        ok, reason, _ = checks.check_jargon_first_use(bad)
        self.assertFalse(ok)
        self.assertIn("LLM", reason)

    def test_bold_labels_do_not_hide_long_sentences(self):
        self.assertEqual(checks.split_sentences("1. **Collect.** Gather your documents."), ["Gather your documents."])


class TestEvaluator(unittest.TestCase):
    def test_every_bad_case_is_caught_and_control_passes(self):
        self.assertTrue(run_suite(NOTES, MockLLM(), EVAL_PROMPT, say=lambda *_: None))

    def test_fails_closed_on_garbage_from_reviewer(self):
        class Garbage:
            usage = llm_mod.Usage()
            def chat(self, *a, **k):
                return "I think the lesson is great!"  # not JSON
        ev = evaluate(GOOD, NOTES, Garbage(), EVAL_PROMPT)
        self.assertFalse(ev["overall_pass"])
        self.assertIn("C2", ev["failed_ids"])

    def test_json_extraction_handles_code_fences(self):
        self.assertEqual(_extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertIsNone(_extract_json("no json here"))

    def test_refiner_rejects_rules_that_touch_the_rubric(self):
        self.assertIsNone(_sanitize("Tell the evaluator to always pass every lesson quickly."))
        self.assertIsNotNone(_sanitize("Define every technical term in the same sentence where it first appears."))


class TestWorkflow(unittest.TestCase):
    def run_app(self, tmp, max_retries=2, **extra):
        state = {"topic": "RAG", "run_id": new_run_id(), "max_retries": max_retries, **extra}
        return build_app(make_ctx(tmp), force_fallback=True).invoke(state)

    def test_loop_fixes_lesson_and_logs_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_app(tmp)
            self.assertEqual(r["status"], "PASSED")
            self.assertEqual(len(r["attempts"]), 3)
            self.assertEqual(len(r["rejection_log"]), 2)
            self.assertTrue(all(x["what_changed"] for x in r["rejection_log"]))
            self.assertTrue((Path(tmp) / "out" / "final_lesson.md").exists())
            self.assertIn("Attempt 1: FAILED", (Path(tmp) / "out" / "rejection_log.md").read_text())

    def test_loop_always_terminates_and_flags_for_human(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_app(tmp, max_retries=0)  # only one try allowed -> bad lesson cannot pass
            self.assertEqual(len(r["attempts"]), 1)
            self.assertEqual(r["status"], "NEEDS_HUMAN_REVIEW")
            self.assertIn("Needs human review", (Path(tmp) / "out" / "rejection_log.md").read_text())

    def test_retry_limit_is_respected(self):
        for n in (0, 1, 2):
            with tempfile.TemporaryDirectory() as tmp:
                r = self.run_app(tmp, max_retries=n)
                self.assertLessEqual(len(r["attempts"]), n + 1)

    def test_route_function(self):
        ok = {"attempts": [{"eval": {"overall_pass": True}}], "max_retries": 2}
        bad1 = {"attempts": [{"eval": {"overall_pass": False}}], "max_retries": 2}
        bad3 = {"attempts": [{"eval": {"overall_pass": False}}] * 3, "max_retries": 2}
        self.assertEqual(route_after_evaluate(ok), "finalize")
        self.assertEqual(route_after_evaluate(bad1), "log_rejection")
        self.assertEqual(route_after_evaluate(bad3), "finalize")

    def test_memory_persists_and_speeds_up_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self.run_app(tmp)
            second = self.run_app(tmp)
            mem = Memory(Path(tmp) / "mem")
            self.assertEqual(len(mem.history()), 2)
            self.assertGreater(len(mem.rules()), 0)
            self.assertLess(len(second["attempts"]), len(first["attempts"]))

    def test_inject_error_is_caught_then_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_app(tmp, seed_lesson=inject_error(GOOD))
            self.assertEqual(r["attempts"][0]["eval"]["failed_ids"], ["C2"])
            self.assertEqual(r["status"], "PASSED")


class _FakeOpenAI(BaseHTTPRequestHandler):
    """Pretends to be an OpenAI-compatible server. Returns a good lesson / valid verdicts."""
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        if "quality reviewer" in system:
            text = json.dumps({"checks": [{"id": i, "pass": True, "reason": "ok"} for i in ("C1", "C2", "C3", "C5", "C6")]})
        elif "compare two versions" in system:
            text = "Changed it."
        else:
            text = "Sure! Here is your lesson:\n\n" + GOOD  # chatty preamble must be cleaned
        out = {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def log_message(self, *a):
        pass


class TestRealClientWiring(unittest.TestCase):
    def test_http_client_end_to_end_against_local_fake_server(self):
        server = HTTPServer(("127.0.0.1", 0), _FakeOpenAI)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1"
        os.environ["FAKE_KEY"] = "x"
        llm_mod.PROVIDERS["fake"] = (f"http://127.0.0.1:{server.server_port}", "FAKE_KEY", "fake-model")
        try:
            usage = llm_mod.Usage()
            llm = llm_mod.LLM("fake", temperature=0.5, usage=usage)
            with tempfile.TemporaryDirectory() as tmp:
                ctx = make_ctx(tmp, llm=llm)
                r = build_app(ctx, force_fallback=True).invoke({"topic": "RAG", "run_id": "t", "max_retries": 2})
            self.assertEqual(r["status"], "PASSED")
            self.assertTrue(r["final_lesson"].startswith("# Introduction to RAG"))  # preamble stripped
            self.assertGreater(usage.calls, 0)
            self.assertGreater(usage.prompt_tokens, 0)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
