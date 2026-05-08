#!/usr/bin/env python3
"""
RAGAS CI evaluation script (ragas >= 0.4 compatible).

Scores a fixed set of mock pipeline responses using RAGAS metrics. No running
Neo4j instance is required — responses are pre-built. Only GOOGLE_API_KEY is
needed.

The test suite deliberately includes one bad answer that hallucinates facts and
ignores the question entirely, causing aggregate faithfulness and answer_relevancy
to drop below threshold and failing the evaluation.

Exit codes
----------
0  All aggregate metrics are at or above their thresholds.
1  One or more metrics fell below threshold, or GOOGLE_API_KEY is missing.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from datasets import Dataset
from google import genai as google_genai
from langchain_google_genai import ChatGoogleGenerativeAI
from ragas import evaluate
from ragas.embeddings import GoogleEmbeddings
# Use the old-style Metric subclasses — ragas.evaluate() validates with
# isinstance(m, ragas.metrics.base.Metric), which the ragas.metrics.collections
# classes do NOT satisfy.
from ragas.metrics._answer_relevance import AnswerRelevancy
from ragas.metrics._context_precision import ContextPrecision
from ragas.metrics._faithfulness import Faithfulness

# ---------------------------------------------------------------------------
# Thresholds — aggregate mean must meet or exceed each value.
# ---------------------------------------------------------------------------
THRESHOLDS: dict[str, float] = {
    "faithfulness": 0.7,
    "answer_relevancy": 0.7,
    "context_precision": 0.6,
}

# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------
# label="pass"  → good, grounded, relevant answer
# label="fail"  → deliberately hallucinated / off-topic answer
#
# 3 passing + 1 failing → aggregate faithfulness/answer_relevancy ≈ 0.65,
# below the 0.7 threshold, so the CI job will exit 1.
# ---------------------------------------------------------------------------
TEST_CASES: list[dict] = [
    # ------------------------------------------------------------------ PASS
    {
        "label": "pass",
        "question": "Who is Imran Khan?",
        "answer": (
            "Imran Khan is a Pakistani politician and former Prime Minister who "
            "founded Pakistan Tehreek-e-Insaf (PTI) in 1996."
        ),
        "contexts": [
            "Imran Khan served as the 22nd Prime Minister of Pakistan from August 2018 to April 2022.",
            "He founded Pakistan Tehreek-e-Insaf (PTI) on April 25, 1996.",
        ],
        "ground_truth": (
            "Imran Khan is a Pakistani politician and former Prime Minister "
            "who founded Pakistan Tehreek-e-Insaf (PTI)."
        ),
    },
    # ------------------------------------------------------------------ PASS
    {
        "label": "pass",
        "question": "Which party did Nawaz Sharif lead?",
        "answer": "Nawaz Sharif led Pakistan Muslim League-Nawaz (PML-N).",
        "contexts": [
            "Nawaz Sharif is the president of Pakistan Muslim League-Nawaz (PML-N) "
            "and has served as Prime Minister three times.",
        ],
        "ground_truth": "Nawaz Sharif led the Pakistan Muslim League-Nawaz (PML-N).",
    },
    # ------------------------------------------------------------------ PASS
    {
        "label": "pass",
        "question": "What position did Benazir Bhutto hold?",
        "answer": (
            "Benazir Bhutto served as Prime Minister of Pakistan and was the first "
            "woman to head the government of a Muslim-majority country."
        ),
        "contexts": [
            "Benazir Bhutto was Prime Minister of Pakistan from 1988 to 1990 and again from 1993 to 1996.",
            "She was the first female head of government of a Muslim-majority nation.",
        ],
        "ground_truth": (
            "Benazir Bhutto served as Prime Minister of Pakistan, "
            "being the first woman to hold this office."
        ),
    },
    # ------------------------------------------------------------------ FAIL  (deliberate)
    # Answer is completely off-topic and introduces hallucinated facts absent
    # from the context. Expected scores:
    #   faithfulness      ~ 0.0  (no claim is grounded in the context)
    #   answer_relevancy  ~ 0.0  (answer does not address the question at all)
    #   context_precision ~ 0.0  (retrieved context is not used)
    {
        "label": "fail",
        "question": "Who founded Pakistan Tehreek-e-Insaf?",
        "answer": (
            "The Pakistan Cricket Board was established in 1952 under the "
            "chairmanship of Justice Cornelius. It is responsible for organising "
            "cricket matches and managing the national team's schedule."
        ),
        "contexts": [
            "Imran Khan founded Pakistan Tehreek-e-Insaf (PTI) on April 25, 1996.",
        ],
        "ground_truth": (
            "Pakistan Tehreek-e-Insaf (PTI) was founded by Imran Khan in 1996."
        ),
    },
]

METRIC_COLS = ["faithfulness", "answer_relevancy", "context_precision"]
RESULTS_PATH = Path("eval_results.json")


def _separator(char: str = "-", width: int = 72) -> str:
    return char * width


def main() -> int:
    api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GOOGLE_API_KEY is not set.", file=sys.stderr)
        return 1

    n_pass = sum(1 for t in TEST_CASES if t["label"] == "pass")
    n_fail = sum(1 for t in TEST_CASES if t["label"] == "fail")
    print(_separator("="))
    print("RAGAS CI Evaluation")
    print(_separator("="))
    print(f"Test cases : {len(TEST_CASES)}  ({n_pass} expected-pass, {n_fail} expected-fail)")
    print(f"Thresholds : {THRESHOLDS}")
    print()

    # ----------------------------------------------------------------
    # LLM: pass ChatGoogleGenerativeAI directly to evaluate() — it
    # auto-wraps any langchain BaseLanguageModel in LangchainLLMWrapper,
    # which is what the old-style MetricWithLLM metrics expect.
    #
    # Embeddings: GoogleEmbeddings satisfies BaseRagasEmbedding, which
    # MetricWithEmbeddings.embeddings accepts.
    #
    # Metrics: fresh instances of the OLD Metric subclasses so that
    # isinstance(m, ragas.metrics.base.Metric) is True.
    # ----------------------------------------------------------------
    genai_client = google_genai.Client(api_key=api_key)
    langchain_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key)
    embeddings = GoogleEmbeddings(client=genai_client, model="gemini-embedding-001")
    metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision()]

    dataset = Dataset.from_dict(
        {
            "question": [t["question"] for t in TEST_CASES],
            "answer": [t["answer"] for t in TEST_CASES],
            "contexts": [t["contexts"] for t in TEST_CASES],
            "ground_truth": [t["ground_truth"] for t in TEST_CASES],
        }
    )

    print("Scoring with RAGAS ...")
    result = evaluate(dataset, metrics=metrics, llm=langchain_llm, embeddings=embeddings)
    scores_df = result.to_pandas()
    available_cols = [c for c in METRIC_COLS if c in scores_df.columns]

    def _safe(val) -> float | None:
        """Return float or None — NaN/Inf are not JSON-serialisable."""
        if val is None:
            return None
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f

    # ----------------------------------------------------------------
    # Per-question report
    # ----------------------------------------------------------------
    print()
    print(_separator())
    print("Per-question results")
    print(_separator())
    per_question_output: list[dict] = []
    for i, case in enumerate(TEST_CASES):
        tag = "[EXPECTED PASS]" if case["label"] == "pass" else "[EXPECTED FAIL]"
        print(f"\n{tag}  Q{i + 1}: {case['question']}")
        print(f"        Answer: {case['answer'][:80]}{'...' if len(case['answer']) > 80 else ''}")
        row: dict = {"question": case["question"], "label": case["label"]}
        for col in available_cols:
            score = _safe(scores_df[col].iloc[i] if i < len(scores_df) else None)
            threshold = THRESHOLDS.get(col, 0.0)
            status = "PASS" if score is not None and score >= threshold else "FAIL"
            score_str = f"{score:.3f}" if score is not None else "n/a"
            print(f"        {col:<22} {score_str}  (threshold={threshold})  [{status}]")
            row[col] = score
        per_question_output.append(row)

    # ----------------------------------------------------------------
    # Aggregate report + pass/fail decision
    # ----------------------------------------------------------------
    print()
    print(_separator("="))
    print("Aggregate scores")
    print(_separator("="))

    aggregate_output: dict[str, float] = {}
    failures: list[str] = []
    for col in available_cols:
        mean = _safe(scores_df[col].mean())
        threshold = THRESHOLDS.get(col, 0.0)
        if mean is None:
            status = "FAIL"
            mean_str = "n/a"
            failures.append(f"{col}=n/a")
        elif mean < threshold:
            status = "FAIL"
            mean_str = f"{mean:.3f}"
            failures.append(f"{col}={mean:.3f} < {threshold}")
        else:
            status = "PASS"
            mean_str = f"{mean:.3f}"
        print(f"  {col:<22} {mean_str}  (threshold={threshold})  [{status}]")
        aggregate_output[col] = mean

    RESULTS_PATH.write_text(
        json.dumps(
            {"aggregate": aggregate_output, "per_question": per_question_output},
            indent=2,
        )
    )

    print()
    print(_separator("="))
    if failures:
        print("RESULT: FAILED")
        print(f"Metrics below threshold: {', '.join(failures)}")
        print()
        print(
            "NOTE: The 'expected-fail' test case deliberately contains a hallucinated,\n"
            "off-topic answer. It drags aggregate faithfulness and answer_relevancy\n"
            "below the 0.7 threshold, causing this evaluation run to fail.\n"
            "Fix the pipeline's retrieval/generation quality to make it pass."
        )
        print(_separator("="))
        return 1

    print("RESULT: PASSED — all metrics above threshold.")
    print(_separator("="))
    return 0


if __name__ == "__main__":
    sys.exit(main())
