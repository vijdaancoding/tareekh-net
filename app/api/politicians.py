import uuid
from fastapi import APIRouter, HTTPException, Query, Depends
from neo4j import AsyncDriver
from app.dependencies import get_neo4j_driver
from app.db.queries import get_all_politicians, get_politician_by_id, semantic_search
from app.models.politician import PoliticianResponse, PoliticianDetailResponse, QueryRequest, QueryResponse
from app.services.embedding_service import embedding_service
from app.agents.graph import query_graph

router = APIRouter()


def _make_query_state(question: str) -> dict:
    return {
        "target_url": "", "query": question, "scraped_sources": [],
        "extracted_entities": None, "cypher_write_query": None,
        "cypher_write_params": None, "hitl_job_id": None,
        "hitl_decision": None, "hitl_feedback": None,
        "query_results": None, "final_answer": None,
        "validation_passed": None, "validation_notes": None,
        "messages": [], "error": None, "retry_count": 0,
    }


@router.get("/politicians", response_model=list[PoliticianResponse])
async def list_politicians(
    query: str | None = Query(None, description="Semantic search query"),
    driver: AsyncDriver = Depends(get_neo4j_driver),
):
    if query:
        embedding = await embedding_service.embed_query(query)
        results = await semantic_search(driver, embedding)
        return [PoliticianResponse(**{k: v for k, v in r.items() if k != "score"}) for r in results]
    rows = await get_all_politicians(driver)
    return [PoliticianResponse(**r) for r in rows]


@router.get("/politicians/{politician_id}", response_model=PoliticianDetailResponse)
async def get_politician(politician_id: str, driver: AsyncDriver = Depends(get_neo4j_driver)):
    result = await get_politician_by_id(driver, politician_id)
    if not result:
        raise HTTPException(status_code=404, detail="Politician not found")
    return PoliticianDetailResponse(**result)


@router.post("/politicians/query", response_model=QueryResponse)
async def query_politicians(request: QueryRequest):
    config = {"configurable": {"thread_id": "query-" + str(uuid.uuid4())}}
    final_state = await query_graph.ainvoke(_make_query_state(request.question), config=config)
    answer = final_state.get("final_answer") or "No answer generated"
    results = final_state.get("query_results") or []
    return QueryResponse(question=request.question, answer=answer, results=results)
