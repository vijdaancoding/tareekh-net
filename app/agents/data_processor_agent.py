import json
import uuid
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.services.embedding_service import embedding_service
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
    """Split markdown on ## headers, then merge small chunks up to max_chars."""
    import re
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
    """Prefer chunks whose headings match relevant political/bio keywords."""
    import re
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
        # Fill up to max_total, truncating the last chunk if needed
        selected += "\n\n" + chunk[:remaining]
    return selected.strip()


def _log(msg: str) -> None:
    print(f"  [DATA PROCESSOR] {msg}", flush=True)


async def data_processor_node(state: AgentState) -> dict:
    if not state.get("scraped_sources"):
        _log("ERROR: No scraped sources available")
        return {"error": "No scraped sources available", "extracted_entities": None}

    # Build chunked, section-aware content from each source
    _log(f"Chunking {len(state['scraped_sources'])} source(s)...")
    combined_content = ""
    for source in state["scraped_sources"]:
        chunks = _chunk_markdown(source["markdown"])
        selected = _select_chunks(chunks, max_total=5000)
        combined_content += f"\n\n=== Source: {source['title']} ===\n{selected}"
        _log(f"  '{source['title']}': {len(chunks)} chunks → {len(selected):,} chars selected")

    combined_content = combined_content[:15000]  # Hard safety cap
    _log(f"Total content sent to LLM: {len(combined_content):,} chars")

    _log("Calling Gemini to extract entities...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)

    response = await llm.ainvoke([
        SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
        HumanMessage(content=f"Extract politician data from:\n{combined_content}")
    ])

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw.strip())
    except Exception as e:
        _log(f"ERROR: LLM extraction failed: {e}\nRaw response: {response.content[:200]}")
        return {"error": f"LLM extraction failed: {e}", "extracted_entities": None}

    _log(f"Extracted: name='{data.get('name')}', born='{data.get('born')}', "
         f"{len(data.get('parties', []))} party(ies), {len(data.get('positions', []))} position(s)")

    # Generate embedding for the bio
    bio = data.get("bio", "")
    embedding = []
    if bio:
        _log("Generating Gemini embedding for bio...")
        try:
            embedding = await embedding_service.embed_text(bio)
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

    # Build parameterized Cypher MERGE query
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

WITH p
UNWIND $parties AS party_data
MERGE (party:Party {id: party_data.id})
SET party.name = party_data.name,
    party.abbreviation = party_data.abbreviation
MERGE (p)-[mem:MEMBER_OF]->(party)
SET mem.from_date = party_data.from_date,
    mem.to_date = party_data.to_date,
    mem.role = party_data.role

WITH p
UNWIND $positions AS pos_data
MERGE (pos:Position {id: pos_data.id})
SET pos.title = pos_data.title,
    pos.level = pos_data.level,
    pos.branch = pos_data.branch
MERGE (p)-[held:HELD_POSITION]->(pos)
SET held.from_date = pos_data.from_date,
    held.to_date = pos_data.to_date,
    held.constituency = pos_data.constituency
"""


def _build_params(entities: dict) -> dict:
    import uuid as uuid_mod
    parties = [
        {
            "id": str(uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, p["name"])),
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
            "id": str(uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, pos["title"] + entities["politician_id"])),
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
        "source_id": str(uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, entities["source_url"])),
        "parties": parties,
        "positions": positions,
    }
