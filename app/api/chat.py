import uuid
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from app.agents.orchestrator_agent import classify_intent, find_wikipedia_url
from app.agents.graph import ingestion_graph, query_graph
from app.services.hitl_store import hitl_store

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(max_length=2000)
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    intent: str
    thread_id: Optional[str] = None
    job_id: Optional[str] = None
    query_results: list[dict] = []
    pending_jobs: list[dict] = []


def _make_initial_state(url: str = "", query: str = "") -> dict:
    return {
        "target_url": url, "query": query, "scraped_sources": [],
        "extracted_entities": None, "cypher_write_query": None,
        "cypher_write_params": None, "hitl_job_id": None,
        "hitl_decision": None, "hitl_feedback": None,
        "query_results": None, "final_answer": None,
        "validation_passed": None, "validation_notes": None,
        "messages": [], "error": None, "retry_count": 0,
    }


async def _run_ingestion(thread_id: str, url: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    try:
        async for _ in ingestion_graph.astream(_make_initial_state(url=url), config=config):
            pass
    except Exception as e:
        print(f"  [CHAT] Ingestion error for thread {thread_id}: {e}", flush=True)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    print(f"  [CHAT] Message: {request.message!r}", flush=True)

    try:
        classified = await classify_intent(request.message)
    except Exception as e:
        return ChatResponse(reply=f"Sorry, I couldn't understand that: {e}", intent="general")

    intent = classified.get("intent", "general")
    reply = classified.get("reply", "")
    print(f"  [CHAT] Intent: {intent}", flush=True)

    # --- INGEST ---
    if intent == "ingest":
        name = classified.get("politician_name")
        if not name:
            return ChatResponse(reply="I couldn't identify a politician name. Please try again.", intent=intent)

        url = await find_wikipedia_url(name)
        if not url:
            return ChatResponse(reply=f"Couldn't find a Wikipedia article for '{name}'.", intent=intent)

        thread_id = str(uuid.uuid4())
        print(f"  [CHAT] Starting ingestion for '{name}' → {url}", flush=True)
        background_tasks.add_task(_run_ingestion, thread_id, url)

        return ChatResponse(
            reply=f"{reply} I found the Wikipedia article for **{name}** and started ingestion (thread: `{thread_id[:8]}…`). This takes ~30 seconds. Check back for a pending approval request.",
            intent=intent,
            thread_id=thread_id,
        )

    # --- QUERY ---
    if intent == "query":
        question = classified.get("question") or request.message
        config = {"configurable": {"thread_id": "chat-" + str(uuid.uuid4())}}
        # ainvoke returns the full accumulated state — reliable for multi-node graphs
        final_state = await query_graph.ainvoke(_make_initial_state(query=question), config=config)
        answer = final_state.get("final_answer") or "No answer found."
        results = final_state.get("query_results") or []
        return ChatResponse(reply=answer, intent=intent, query_results=results)

    # --- PENDING ---
    if intent == "pending":
        jobs = hitl_store.list_pending()
        if not jobs:
            return ChatResponse(reply="No pending approval requests right now.", intent=intent)
        job_list = [{"job_id": j.job_id, "politician_name": j.politician_name, "status": j.status} for j in jobs]
        names = ", ".join(j.politician_name for j in jobs)
        return ChatResponse(
            reply=f"There are **{len(jobs)}** pending approval(s): {names}. Use the approval panel to review.",
            intent=intent,
            pending_jobs=job_list,
        )

    # --- GENERAL ---
    return ChatResponse(reply=reply or "How can I help you with Pakistani politicians?", intent=intent)
