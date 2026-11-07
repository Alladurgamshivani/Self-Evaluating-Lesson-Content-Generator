"""Deterministic (code) checks. No LLM is used here, so results are exact and repeatable.

Each function returns (passed: bool, reason: str, metrics: dict).
"""
from __future__ import annotations

import re
from statistics import mean

# --- configuration -----------------------------------------------------------------------------

MAX_AVG_SENTENCE_WORDS = 15
LONG_SENTENCE_WORDS = 25
MAX_LONG_SENTENCE_SHARE = 0.10
MIN_WORDS, MAX_WORDS = 500, 1200

# (key, human heading, regex that must match the heading text)
REQUIRED_SECTIONS = [
    ("hook", "Hook", r"hook"),
    ("what", "What Is It?", r"\bwhat\b"),
    ("why", "Why It Matters", r"\bwhy\b"),
    ("how", "How It Works", r"\bhow\b"),
    ("example", "Example", r"example"),
    ("recap", "Recap", r"recap"),
    ("check", "Check Yourself", r"check"),
]

# Technical terms that must be explained at first use. Extend this list for other topics.
JARGON_TERMS = ["LLM", "embedding", "vector database", "hallucination", "chunk", "prompt"]
CASE_SENSITIVE_TERMS = {"LLM"}

DEFINITION_MARKER = re.compile(
    r"\b(is|are|means|mean|called|stands for|short for|refers to|known as)\b", re.IGNORECASE
)

# --- text helpers ------------------------------------------------------------------------------


def strip_markdown(text: str) -> str:
    """Remove markdown so we count only the words a learner actually reads."""
    text = text.replace("\u2011", "-").replace("\u2010", "-")  # models often emit non-breaking hyphens
    text = re.sub(r"```.*?```", " ", text, flags=re.S)  # code fences
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or re.match(r"^\|.*\|$", s) or re.match(r"^[-=_]{3,}$", s):
            continue
        s = re.sub(r"^([-*+]|\d+[.)])\s+", "", s)  # bullet / number prefix
        # A bold step label such as "**Collect.**" is a title, not a sentence: drop it so it cannot
        # make the average sentence length look shorter than it really is.
        s = re.sub(r"^\*\*[^*]{1,60}\.\*\*\s+(?=\S)", "", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)  # links
        s = re.sub(r"[*_`]+", "", s)  # bold / italic / code marks
        lines.append(s)
    return "\n".join(lines)


def split_sentences(text: str) -> list[str]:
    """Split markdown text into sentences (headings removed). Simple and predictable on purpose."""
    plain = strip_markdown(text)
    for abbr, rep in (("e.g.", "eg"), ("i.e.", "ie"), ("vs.", "vs"), ("Dr.", "Dr"), ("Mr.", "Mr")):
        plain = plain.replace(abbr, rep)
    sentences: list[str] = []
    for line in plain.splitlines():
        for part in re.split(r"(?<=[.!?])[\"'”’]?\s+", line):
            part = part.strip()
            if re.search(r"\w", part):
                sentences.append(part)
    return sentences


def count_words(sentence: str) -> int:
    return len(re.findall(r"[A-Za-z0-9’'\-]+", sentence))


def get_sections(lesson: str) -> list[tuple[str, str]]:
    """Return [(heading_text, body_text)] for every level-2 heading (## ...)."""
    sections: list[tuple[str, str]] = []
    heading, body = None, []
    for line in lesson.splitlines():
        m = re.match(r"^##\s+(.*?)\s*$", line)
        if m and not line.startswith("###"):
            if heading is not None:
                sections.append((heading, "\n".join(body)))
            heading, body = m.group(1), []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body)))
    return sections


def find_section(lesson: str, regex: str) -> str | None:
    for heading, body in get_sections(lesson):
        if re.search(regex, heading, re.IGNORECASE):
            return body
    return None


# --- the checks --------------------------------------------------------------------------------


def check_readability(lesson: str):
    """C4: average sentence length and share of very long sentences."""
    sentences = split_sentences(lesson)
    if not sentences:
        return False, "No readable sentences found.", {}
    lengths = [count_words(s) for s in sentences]
    avg = mean(lengths)
    long_ones = [s for s, n in zip(sentences, lengths) if n > LONG_SENTENCE_WORDS]
    share = len(long_ones) / len(sentences)
    metrics = {
        "sentences": len(sentences),
        "avg_words_per_sentence": round(avg, 1),
        "long_sentences": len(long_ones),
        "long_share": round(share, 3),
    }
    problems = []
    if avg > MAX_AVG_SENTENCE_WORDS:
        problems.append(f"average sentence length is {avg:.1f} words (limit {MAX_AVG_SENTENCE_WORDS})")
    if share > MAX_LONG_SENTENCE_SHARE:
        example = long_ones[0][:90] + ("..." if len(long_ones[0]) > 90 else "")
        problems.append(
            f"{len(long_ones)} of {len(sentences)} sentences are over {LONG_SENTENCE_WORDS} words "
            f"(limit {int(MAX_LONG_SENTENCE_SHARE * 100)}%), e.g. \"{example}\""
        )
    if problems:
        return False, "; ".join(problems) + ".", metrics
    return True, f"Average sentence length is {avg:.1f} words; long sentences are {share:.0%}.", metrics


def check_structure(lesson: str):
    """C6 (code half): required level-2 headings present and in order."""
    headings = [h for h, _ in get_sections(lesson)]
    pos = -1
    missing = []
    for _, human, rx in REQUIRED_SECTIONS:
        idx = next((i for i, h in enumerate(headings) if i > pos and re.search(rx, h, re.IGNORECASE)), None)
        if idx is None:
            missing.append(human)
        else:
            pos = idx
    if missing:
        return (
            False,
            "Missing or out-of-order section(s): " + ", ".join(f"'{m}'" for m in missing) + ".",
            {"headings_found": headings},
        )
    return True, "All 7 required sections are present in the right order.", {"headings_found": headings}


def check_recap_and_quiz(lesson: str):
    """C7: recap has >=3 points, Check Yourself has >=3 questions."""
    recap = find_section(lesson, r"recap")
    quiz = find_section(lesson, r"check")
    problems = []
    recap_points = 0
    if recap is None:
        problems.append("there is no Recap section")
    else:
        bullets = [ln for ln in recap.splitlines() if re.match(r"^\s*([-*+]|\d+[.)])\s+\S", ln)]
        recap_points = len(bullets) or len(split_sentences(recap))
        if recap_points < 3:
            problems.append(f"Recap has only {recap_points} point(s), needs at least 3")
    questions = 0
    if quiz is None:
        problems.append("there is no Check Yourself section")
    else:
        questions = quiz.count("?")
        if questions < 3:
            problems.append(f"Check Yourself has {questions} question(s) ending with '?', needs at least 3")
    metrics = {"recap_points": recap_points, "questions": questions}
    if problems:
        return False, "; ".join(problems).capitalize() + ".", metrics
    return True, f"Recap has {recap_points} points and Check Yourself has {questions} questions.", metrics


def check_length(lesson: str):
    """C8: word count between MIN_WORDS and MAX_WORDS."""
    words = count_words(strip_markdown(lesson))
    metrics = {"words": words}
    if words < MIN_WORDS:
        return False, f"Lesson is too short: {words} words (minimum {MIN_WORDS}).", metrics
    if words > MAX_WORDS:
        return False, f"Lesson is too long: {words} words (maximum {MAX_WORDS}).", metrics
    return True, f"Length is {words} words.", metrics


def _term_regex(term: str) -> re.Pattern:
    flags = 0 if term in CASE_SENSITIVE_TERMS else re.IGNORECASE
    return re.compile(r"\b" + re.escape(term) + r"(?:s|es)?\b", flags)


def _defines(term: str, sentence: str) -> bool:
    """Does this sentence actually define THIS term? (not just contain some definition word)"""
    t = re.escape(term) + r"(?:s|es)?"
    flags = 0 if term in CASE_SENSITIVE_TERMS else re.IGNORECASE
    patterns = [
        rf"\b{t}\b[^.?!]{{0,40}}?\b(is|are|means|mean|stands for|refers to|is called|is short for)\b",  # "X is ..."
        rf"\b(called|known as|named|short for|stands for)\s+(a |an |the )?{t}\b",                       # "called X"
        rf"\b{t}\s*\(",                                                                                 # "X (meaning...)"
        rf"\(\s*{t}\s*\)",                                                                              # "long name (X)"
        rf"^\W*{t}\b\s*[\u2013\u2014:\-]\s+\S",                                                        # "Embedding - a list of ..."
    ]
    return any(re.search(p, sentence, flags) for p in patterns)


def check_jargon_first_use(lesson: str, terms: list[str] | None = None):
    """C3 (code half): each technical term must be defined where it FIRST appears.

    The sentence of the first use (or the sentence right after it) must define that same term, for example
    "An embedding is ...", "... called a chunk", or "large language model (LLM)". Using a term inside a
    sentence that only defines a different term does not count. The LLM reviewer still judges whether
    the definition is clear; this check cannot be talked into passing by a lenient model.
    """
    terms = terms or JARGON_TERMS
    sentences = split_sentences(lesson)
    unexplained = []
    for term in terms:
        rx = _term_regex(term)
        idx = next((i for i, s in enumerate(sentences) if rx.search(s)), None)
        if idx is None:
            continue  # term not used, nothing to explain
        nxt = sentences[idx + 1] if idx + 1 < len(sentences) else ""
        if not (_defines(term, sentences[idx]) or _defines(term, nxt)):
            unexplained.append((term, sentences[idx]))
    metrics = {"unexplained_terms": [t for t, _ in unexplained]}
    if unexplained:
        term, sent = unexplained[0]
        names = ", ".join(f"'{t}'" for t, _ in unexplained)
        return (
            False,
            f"Technical term(s) used before they are defined: {names}. "
            f"First use of '{term}': \"{sent[:100]}\"",
            metrics,
        )
    return True, "Every technical term is defined at first use.", metrics


# Registry used by the evaluator: check id -> function
CODE_CHECKS = {
    "C3": check_jargon_first_use,
    "C4": check_readability,
    "C6": check_structure,
    "C7": check_recap_and_quiz,
    "C8": check_length,
}