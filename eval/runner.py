import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from datasets import Dataset
from ragas import evaluate
# Use the old-style Metric subclasses — ragas.evaluate() validates with
# isinstance(m, ragas.metrics.base.Metric), which the ragas.metrics.collections
# classes do NOT satisfy. The private _faithfulness etc. modules contain the
# correct hierarchy.
from ragas.metrics._faithfulness import Faithfulness
from ragas.metrics._answer_relevance import AnswerRelevancy
from ragas.metrics._context_precision import ContextPrecision
from ragas.embeddings import GoogleEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai as google_genai

from app.config import settings
from eval.dataset import GOLDEN_DATASET
from eval.pipeline import run_all


async def run_evaluation() -> dict:
    questions = [item["question"] for item in GOLDEN_DATASET]
    ground_truths = [item["ground_truth"] for item in GOLDEN_DATASET]

    pipeline_outputs = await run_all(questions)

    ragas_dataset = Dataset.from_dict(
        {
            "question": [o["question"] for o in pipeline_outputs],
            "answer": [o["answer"] for o in pipeline_outputs],
            "contexts": [o["contexts"] for o in pipeline_outputs],
            "ground_truth": ground_truths,
        }
    )

    # Fresh instances each call — avoids mutating shared singletons.
    # evaluate() auto-injects llm/embeddings into MetricWithLLM /
    # MetricWithEmbeddings fields that are still None.
    langchain_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.google_api_key,
    )
    genai_client = google_genai.Client(api_key=settings.google_api_key)
    embeddings = GoogleEmbeddings(client=genai_client, model="gemini-embedding-001")
    metrics = [Faithfulness(), AnswerRelevancy(), ContextPrecision()]

    # ragas.evaluate() calls asyncio.run() internally, which raises RuntimeError
    # when a uvloop is already running (FastAPI). Running it in a
    # ThreadPoolExecutor gives it a clean thread with no running loop.
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = await loop.run_in_executor(
            pool,
            lambda: evaluate(
                ragas_dataset,
                metrics=metrics,
                llm=langchain_llm,
                embeddings=embeddings,
            ),
        )

    scores_df = result.to_pandas()
    metric_cols = [
        c
        for c in ["faithfulness", "answer_relevancy", "context_precision"]
        if c in scores_df.columns
    ]

    def _safe(val) -> float | None:
        """Return float or None — NaN/Inf are not JSON-serialisable."""
        if val is None:
            return None
        f = float(val)
        return None if (math.isnan(f) or math.isinf(f)) else f

    per_question = []
    for i, q in enumerate(questions):
        row = {"question": q}
        for col in metric_cols:
            val = scores_df[col].iloc[i] if i < len(scores_df) else None
            row[col] = _safe(val)
        per_question.append(row)

    aggregate = {col: _safe(scores_df[col].mean()) for col in metric_cols}
    return {"aggregate": aggregate, "per_question": per_question}
