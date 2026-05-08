from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from langgraph.types import Command
from app.services.hitl_store import hitl_store, HITLJob
from app.agents.graph import ingestion_graph

router = APIRouter()


class HITLJobResponse(BaseModel):
    job_id: str
    thread_id: str
    politician_name: str
    cypher_query: str
    status: str
    created_at: str


class ApproveRequest(BaseModel):
    feedback: Optional[str] = None


class RejectRequest(BaseModel):
    feedback: Optional[str] = "Rejected by reviewer"


def _job_to_response(job: HITLJob) -> HITLJobResponse:
    return HITLJobResponse(
        job_id=job.job_id,
        thread_id=job.thread_id,
        politician_name=job.politician_name,
        cypher_query=job.cypher_query,
        status=job.status,
        created_at=job.created_at.isoformat(),
    )


@router.get("/pending", response_model=list[HITLJobResponse])
async def get_pending():
    return [_job_to_response(j) for j in hitl_store.list_pending()]


@router.post("/approve/{job_id}")
async def approve_job(job_id: str, request: ApproveRequest = ApproveRequest()):
    job = hitl_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "pending":
        raise HTTPException(status_code=400, detail=f"Job is already {job.status}")

    config = {"configurable": {"thread_id": job.thread_id}}
    decision = {"decision": "approved", "feedback": request.feedback or ""}

    try:
        async for _ in ingestion_graph.astream(
            Command(resume=decision), config=config
        ):
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}")

    return {"message": f"Job {job_id} approved and write executed"}


@router.post("/reject/{job_id}")
async def reject_job(job_id: str, request: RejectRequest = RejectRequest()):
    job = hitl_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "pending":
        raise HTTPException(status_code=400, detail=f"Job is already {job.status}")

    config = {"configurable": {"thread_id": job.thread_id}}
    decision = {"decision": "rejected", "feedback": request.feedback or ""}

    try:
        async for _ in ingestion_graph.astream(
            Command(resume=decision), config=config
        ):
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}")

    return {"message": f"Job {job_id} rejected"}
