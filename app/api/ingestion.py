import uuid
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.agents.graph import ingestion_graph

router = APIRouter()


class IngestRequest(BaseModel):
    url: str


class IngestResponse(BaseModel):
    thread_id: str
    message: str


async def run_ingestion(thread_id: str, url: str):
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "target_url": url,
        "query": None,
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
    try:
        async for _ in ingestion_graph.astream(initial_state, config=config):
            pass
    except Exception as e:
        print(f"Ingestion error for thread {thread_id}: {e}")


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    thread_id = str(uuid.uuid4())
    background_tasks.add_task(run_ingestion, thread_id, request.url)
    return IngestResponse(
        thread_id=thread_id,
        message="Ingestion started. Use thread_id to track progress.",
    )
