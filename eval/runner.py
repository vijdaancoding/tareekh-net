import asyncio
from concurrent.futures import ThreadPoolExecutor
from datasets import Dataset
from ragas import evaluate
from ragas.metrics.collections import faithfulness, answer_relevancy, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.config import settings
from eval.dataset import GOLDEN_DATASET
from eval.pipeline import run_all


def _build_ragas_llm() -> LangchainLLMWrapper:
    return LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.google_api_key,
        )
    )


def _build_ragas_embeddings() -> LangchainEmbeddingsWrapper:
    return LangchainEmbeddingsWrapper(
        GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.google_api_key,
        )
    )


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

    ragas_llm = _build_ragas_llm()
    ragas_embeddings = _build_ragas_embeddings()

    metrics = [faithfulness, answer_relevancy, context_precision]
    for metric in metrics:
        metric.llm = ragas_llm
        if hasattr(metric, "embeddings"):
            metric.embeddings = ragas_embeddings

    # ragas.evaluate() is synchronous and internally calls asyncio.run(),
    # which fails inside uvloop's already-running event loop. Running it in
    # a ThreadPoolExecutor gives it a clean thread with no running loop.
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = await loop.run_in_executor(
            pool, lambda: evaluate(ragas_dataset, metrics=metrics)
        )
    scores_df = result.to_pandas()

    metric_cols = [c for c in ["faithfulness", "answer_relevancy", "context_precision"] if c in scores_df.columns]

    per_question = []
    for i, q in enumerate(questions):
        row = {"question": q}
        for col in metric_cols:
            val = scores_df[col].iloc[i] if i < len(scores_df) else None
            row[col] = float(val) if val is not None else None
        per_question.append(row)

    aggregate = {col: float(scores_df[col].mean()) for col in metric_cols}

    return {"aggregate": aggregate, "per_question": per_question}
