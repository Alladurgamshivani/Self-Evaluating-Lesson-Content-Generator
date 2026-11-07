"""Optional Streamlit page on top of the same pipeline (NOT required by the assignment).

Install:  pip install streamlit
Run:      streamlit run app.py

It calls the same graph, evaluator and memory as `python main.py`. Nothing is duplicated.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from main import build_context
from src import llm as llm_mod
from src.graph import build_app, new_run_id

ROOT = Path(__file__).resolve().parent


def run_pipeline(topic: str, max_retries: int, mock: bool) -> dict:
    """Run one full generate -> evaluate -> regenerate loop and return everything the page needs."""
    args = SimpleNamespace(mock=mock, memory_dir=None, out_dir=None, glossary=None)
    ctx = build_context(args)
    log: list[str] = []
    ctx.say = log.append  # collect the console messages instead of printing them
    state = {"topic": topic, "run_id": new_run_id(), "max_retries": max_retries}
    result = build_app(ctx).invoke(state)
    return {
        "status": result["status"],
        "lesson": result["final_lesson"],
        "rejection_log": (ctx.out_dir / "rejection_log.md").read_text(encoding="utf-8"),
        "rules": ctx.memory.rules(),
        "proposals": ctx.memory.proposals(),
        "log": "\n".join(log),
    }


def main() -> None:
    st.set_page_config(page_title="Self-Evaluating Lesson Generator", layout="wide")
    st.title("Self-Evaluating Lesson Generator")
    st.caption("Generate, then evaluate against 8 hard pass/fail checks, then regenerate until it passes (or flag for a human).")

    with st.sidebar:
        topic = st.text_input("Topic", "Introduction to RAG")
        max_retries = st.slider("Max retries", 0, 3, 2)
        mock = st.checkbox("Mock model (no API key, tests the loop only)", value=False)
        go = st.button("Generate lesson", type="primary")

    if go:
        try:
            with st.spinner("Generating and evaluating... free-tier rate limits can make this take a few minutes."):
                st.session_state["result"] = run_pipeline(topic, max_retries, mock)
        except llm_mod.LLMError as e:
            st.error(f"Model call failed: {e}")

    result = st.session_state.get("result")
    if not result:
        st.info("Choose a topic in the sidebar and click Generate lesson.")
        return

    if result["status"] == "PASSED":
        st.success("PASSED: all 8 checks passed.")
    else:
        st.warning("NEEDS HUMAN REVIEW: the retry limit was reached. Read the rejection log.")

    lesson_tab, log_tab, memory_tab, console_tab = st.tabs(["Lesson", "Rejection log", "Memory", "Run console"])
    with lesson_tab:
        st.markdown(result["lesson"])
    with log_tab:
        st.markdown(result["rejection_log"])
    with memory_tab:
        st.subheader("Learned rules")
        for r in result["rules"]:
            st.write(f"**{r['id']}** [{r['check_id']}] {r['rule']}")
        if not result["rules"]:
            st.write("No rules yet.")
        st.subheader("Rubric proposals (pending human review)")
        for p in result["proposals"]:
            st.write(f"**{p['id']}** [{p['check_id']}] {p['proposal']}")
    with console_tab:
        st.code(result["log"])


if __name__ == "__main__":
    main()
