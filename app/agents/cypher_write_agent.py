import uuid
from langgraph.types import interrupt, Command
from langgraph.config import get_config
from app.agents.state import AgentState
from app.services.hitl_store import hitl_store
from app.db.neo4j_client import get_driver


def _log(msg: str) -> None:
    print(f"  [CYPHER WRITE] {msg}", flush=True)


async def cypher_write_node(state: AgentState) -> dict:
    entities = state.get("extracted_entities", {})
    politician_name = entities.get("name", "Unknown") if entities else "Unknown"
    cypher_query = state.get("cypher_write_query", "")
    cypher_params = state.get("cypher_write_params", {})

    config = get_config()
    thread_id = config.get("configurable", {}).get("thread_id", str(uuid.uuid4()))

    # Create HITL job before interrupting
    job = hitl_store.create_job(
        thread_id=thread_id,
        politician_name=politician_name,
        cypher_query=cypher_query,
        cypher_params=cypher_params,
    )
    _log(f"HITL job created: job_id={job.job_id}, politician='{politician_name}'")
    _log("Waiting for human approval — call POST /api/v1/approve/{job_id} or /reject/{job_id}")

    # Interrupt and wait for human decision
    decision = interrupt({
        "job_id": job.job_id,
        "politician_name": politician_name,
        "cypher_query": cypher_query,
        "message": "Please review and approve or reject the Cypher write query.",
    })

    hitl_decision = decision.get("decision", "rejected") if isinstance(decision, dict) else "rejected"
    hitl_feedback = decision.get("feedback", "") if isinstance(decision, dict) else ""

    hitl_store.update_status(job.job_id, hitl_decision, hitl_feedback)
    _log(f"Decision received: {hitl_decision}" + (f" — {hitl_feedback}" if hitl_feedback else ""))

    return {
        "hitl_job_id": job.job_id,
        "hitl_decision": hitl_decision,
        "hitl_feedback": hitl_feedback,
    }


async def execute_write_node(state: AgentState) -> dict:
    name = state.get("extracted_entities", {}).get("name", "Unknown")
    cypher_query = state.get("cypher_write_query", "")
    cypher_params = state.get("cypher_write_params", {})
    _log(f"Writing '{name}' to Neo4j...")

    if not cypher_query:
        _log("ERROR: No Cypher query to execute")
        return {"error": "No Cypher query to execute"}

    try:
        driver = await get_driver()
        async with driver.session() as session:
            await session.run(cypher_query, cypher_params)
        _log(f"Successfully ingested '{name}' into Neo4j")
        return {"error": None, "final_answer": f"Successfully ingested politician: {name}"}
    except Exception as e:
        _log(f"ERROR: Write failed: {e}")
        return {"error": f"Write failed: {e}"}


def hitl_router(state: AgentState) -> str:
    if state.get("hitl_decision") == "approved":
        return "execute_write"
    return "end"
