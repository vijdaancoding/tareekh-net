import uuid
import asyncio
from app.agents.graph import query_graph


def _make_query_state(question: str) -> dict:
    return {
        "target_url": "",
        "query": question,
        "scraped_sources": [],
        "extracted_entities": None,
        "cypher_write_query": None,
        "cypher_write_params": None,
        "hitl_job_id": None,
        "hitl_decision": None,
        "hitl_feedback": None,
        "query_results": None,
        "final_answer": None,
        "validation_passed": None,
        "validation_notes": None,
        "messages": [],
        "error": None,
        "retry_count": 0,
    }


async def run_query(question: str) -> dict:
    config = {"configurable": {"thread_id": "eval-" + str(uuid.uuid4())}}
    final = await query_graph.ainvoke(_make_query_state(question), config=config)
    raw_results = final.get("query_results") or []
    contexts = [str(r) for r in raw_results] if raw_results else [""]
    return {
        "question": question,
        "answer": final.get("final_answer") or "",
        "contexts": contexts,
    }


async def run_all(questions: list[str]) -> list[dict]:
    return await asyncio.gather(*[run_query(q) for q in questions])
