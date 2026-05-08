import json
import re
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.services.embedding_service import embedding_service
from app.utils import strip_code_fence
from app.config import settings

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction expert specializing in Pakistani politics.
Extract structured information about the politician from the provided Wikipedia content.
Return a JSON object with this exact schema:
{
  "name": "Full name",
  "born": "YYYY-MM-DD or YYYY or null",
  "bio": "2-3 sentence biography summary",
  "parties": [
    {"name": "Party name", "abbreviation": "PTI/PMLN/PPP/etc", "from_date": "YYYY or null", "to_date": "YYYY or null", "role": "Member/Chairman/etc or null"}
  ],
  "positions": [
    {"title": "Position title", "level": "federal or provincial", "branch": "executive or legislative or judicial", "from_date": "YYYY or null", "to_date": "YYYY or null", "constituency": "constituency name or null"}
  ]
}
Return only the JSON object, no other text."""


_RELEVANT_SECTIONS = {
    "early life", "personal life", "biography", "background",
    "political career", "political life", "political", "politics",
    "prime minister", "presidency", "government", "tenure",
    "party", "election", "offices", "positions",
}


def _chunk_markdown(markdown: str, max_chars: int = 3000) -> list[str]:
    sections = re.split(r"(?m)^(#{1,3} .+)$", markdown)
    chunks: list[str] = []
    current = ""
    for part in sections:
        if len(current) + len(part) > max_chars:
            if current.strip():
                chunks.append(current.strip())
            current = part
        else:
            current += "\n" + part
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _select_chunks(chunks: list[str], max_total: int = 8000) -> str:
    priority: list[str] = []
    fallback: list[str] = []
    for chunk in chunks:
        m = re.match(r"^#{1,3} (.+)", chunk)
        heading = m.group(1).lower() if m else chunk[:80].lower()
        if any(kw in heading for kw in _RELEVANT_SECTIONS):
            priority.append(chunk)
        else:
            fallback.append(chunk)

    selected = ""
    for chunk in priority + fallback:
        remaining = max_total - len(selected)
        if remaining <= 0:
            break
        selected += "\n\n" + chunk[:remaining]
    return selected.strip()


def _log(msg: str) -> None:
    print(f"  [DATA PROCESSOR] {msg}", flush=True)


async def data_processor_node(state: AgentState) -> dict:
    if not state.get("scraped_sources"):
        _log("ERROR: No scraped sources available")
        return {"error": "No scraped sources available", "extracted_entities": None}

    _log(f"Chunking {len(state['scraped_sources'])} source(s)...")
    combined_content = ""
    for source in state["scraped_sources"]:
        chunks = _chunk_markdown(source["markdown"])
        selected = _select_chunks(chunks, max_total=5000)
        combined_content += f"\n\n=== Source: {source['title']} ===\n{selected}"
        _log(f"  '{source['title']}': {len(chunks)} chunks → {len(selected):,} chars selected")

    combined_content = combined_content[:15000]
    _log(f"Total content sent to LLM: {len(combined_content):,} chars")

    _log("Calling Gemini to extract entities...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
    response = await llm.ainvoke([
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract politician data from the following scraped content:\n<SCRAPED_CONTENT>\n{combined_content}\n</SCRAPED_CONTENT>")
    ])

    try:
        data = json.loads(strip_code_fence(response.content))
    except Exception as e:
        _log(f"ERROR: LLM extraction failed: {e}\nRaw response: {response.content[:200]}")
        return {"error": f"LLM extraction failed: {e}", "extracted_entities": None}

    _log(f"Extracted: name='{data.get('name')}', born='{data.get('born')}', "
         f"{len(data.get('parties', []))} party(ies), {len(data.get('positions', []))} position(s)")

    bio = data.get("bio", "")

    # Build a richer text for embedding: name + bio + party/position context
    parties_str = ", ".join(p["name"] for p in data.get("parties", []))
    positions_str = ", ".join(p["title"] for p in data.get("positions", []))
    embed_text = data.get("name", "")
    if bio:
        embed_text += f". {bio}"
    if parties_str:
        embed_text += f" Parties: {parties_str}."
    if positions_str:
        embed_text += f" Positions: {positions_str}."

    embedding: list[float] = []
    if embed_text:
        _log("Generating Gemini embedding...")
        try:
            embedding = await embedding_service.embed_document(embed_text)
            _log(f"Embedding generated ({len(embedding)}-dim)")
        except Exception as e:
            _log(f"ERROR: Embedding failed: {e}")
            return {"error": f"Embedding failed: {e}", "extracted_entities": None}

    politician_id = str(uuid.uuid4())
    entities = {
        "politician_id": politician_id,
        "name": data.get("name", "Unknown"),
        "born": data.get("born"),
        "bio": bio,
        "embedding": embedding,
        "parties": data.get("parties", []),
        "positions": data.get("positions", []),
        "source_url": state["scraped_sources"][0]["url"],
    }

    _log("Building Cypher MERGE query...")
    cypher_query = _build_cypher(entities)
    cypher_params = _build_params(entities)
    _log("Data processor done — ready for validation")

    return {
        "extracted_entities": entities,
        "cypher_write_query": cypher_query,
        "cypher_write_params": cypher_params,
        "error": None,
    }


def _build_cypher(entities: dict) -> str:
    # Only politician + source nodes; parties/positions are written separately
    # in execute_write_node to avoid empty-UNWIND dropping all rows.
    return """
MERGE (p:Politician {id: $politician_id})
SET p.name = $name,
    p.born = $born,
    p.bio = $bio,
    p.embedding = $embedding

MERGE (src:Source {url: $source_url})
SET src.id = $source_id,
    src.scraped_at = datetime()
MERGE (p)-[:SOURCED_FROM]->(src)
"""


def _build_params(entities: dict) -> dict:
    parties = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, p["name"])),
            "name": p["name"],
            "abbreviation": p.get("abbreviation", ""),
            "from_date": p.get("from_date"),
            "to_date": p.get("to_date"),
            "role": p.get("role"),
        }
        for p in entities["parties"]
    ]
    positions = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, pos["title"] + entities["politician_id"])),
            "title": pos["title"],
            "level": pos.get("level", "federal"),
            "branch": pos.get("branch", "executive"),
            "from_date": pos.get("from_date"),
            "to_date": pos.get("to_date"),
            "constituency": pos.get("constituency"),
        }
        for pos in entities["positions"]
    ]
    return {
        "politician_id": entities["politician_id"],
        "name": entities["name"],
        "born": entities["born"],
        "bio": entities["bio"],
        "embedding": entities["embedding"],
        "source_url": entities["source_url"],
        "source_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, entities["source_url"])),
        "parties": parties,
        "positions": positions,
    }
