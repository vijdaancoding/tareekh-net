import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HITLJob:
    job_id: str
    thread_id: str
    politician_name: str
    cypher_query: str
    cypher_params: dict
    status: str = "pending"  # pending | approved | rejected
    feedback: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class HITLStore:
    def __init__(self):
        self._jobs: dict[str, HITLJob] = {}
        self._thread_to_job: dict[str, str] = {}

    def create_job(
        self,
        thread_id: str,
        politician_name: str,
        cypher_query: str,
        cypher_params: dict,
    ) -> HITLJob:
        job_id = str(uuid.uuid4())
        job = HITLJob(
            job_id=job_id,
            thread_id=thread_id,
            politician_name=politician_name,
            cypher_query=cypher_query,
            cypher_params=cypher_params,
        )
        self._jobs[job_id] = job
        self._thread_to_job[thread_id] = job_id
        return job

    def get_job(self, job_id: str) -> HITLJob | None:
        return self._jobs.get(job_id)

    def get_job_by_thread(self, thread_id: str) -> HITLJob | None:
        job_id = self._thread_to_job.get(thread_id)
        return self._jobs.get(job_id) if job_id else None

    def list_pending(self) -> list[HITLJob]:
        return [j for j in self._jobs.values() if j.status == "pending"]

    def update_status(self, job_id: str, status: str, feedback: str | None = None) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.status = status
        job.feedback = feedback
        return True


hitl_store = HITLStore()
