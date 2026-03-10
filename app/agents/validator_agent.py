from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.config import settings


def _log(msg: str) -> None:
    print(f"  [VALIDATOR] {msg}", flush=True)


async def validator_node(state: AgentState) -> dict:
    entities = state.get("extracted_entities")
    retry_count = state.get("retry_count", 0)
    _log(f"Running validation (attempt {retry_count + 1}/3)...")

    if not entities:
        _log("ERROR: No entities to validate")
        return {"validation_passed": False, "validation_notes": "No entities to validate"}

    notes = []

    # Completeness check
    if not entities.get("name") or entities["name"] == "Unknown":
        notes.append("Missing politician name")
    if not entities.get("bio"):
        notes.append("Missing biography")
    if not entities.get("born"):
        notes.append("Warning: birth date not found (non-critical)")

    # Date consistency check for parties
    parties = entities.get("parties", [])
    for i, p1 in enumerate(parties):
        for p2 in parties[i + 1:]:
            if p1.get("to_date") is None and p2.get("to_date") is None and p1["name"] != p2["name"]:
                notes.append(f"Possible overlap: both {p1['name']} and {p2['name']} have no end date")

    critical_errors = [n for n in notes if not n.startswith("Warning")]

    if critical_errors:
        _log(f"Critical errors found: {critical_errors}")
        if retry_count < 2:
            _log(f"Retrying data processor (retry {retry_count + 1}/2)...")
            return {
                "validation_passed": False,
                "validation_notes": "; ".join(notes),
                "retry_count": retry_count + 1,
            }
        else:
            _log("Max retries reached — failing validation")
            return {
                "validation_passed": False,
                "validation_notes": f"Validation failed after retries: {'; '.join(notes)}",
            }

    # Cross-source consistency check (LLM-based)
    n_sources = len(state.get("scraped_sources", []))
    if n_sources > 1:
        _log(f"Running cross-source consistency check ({n_sources} sources)...")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
        source_summaries = "\n".join(
            f"Source {i+1} ({s['title']}): {s['markdown'][:500]}"
            for i, s in enumerate(state["scraped_sources"])
        )
        check_response = await llm.ainvoke([
            SystemMessage(content="Check if there are any major contradictions between these sources about the same politician. Reply with 'CONSISTENT' or 'CONTRADICTIONS: <details>'."),
            HumanMessage(content=source_summaries)
        ])
        verdict = check_response.content[:80].strip()
        _log(f"Cross-source verdict: {verdict}")
        if "CONTRADICTIONS" in check_response.content.upper():
            notes.append(f"Cross-source note: {check_response.content}")

    summary = "; ".join(notes) if notes else "All checks passed"
    _log(f"Validation PASSED — {summary}")
    return {
        "validation_passed": True,
        "validation_notes": summary,
        "error": None,
    }


def validation_router(state: AgentState) -> str:
    if state.get("validation_passed"):
        return "cypher_write"
    if state.get("retry_count", 0) < 2:
        return "data_processor"
    return "end_failed"
