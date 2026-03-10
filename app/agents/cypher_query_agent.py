import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.services.embedding_service import embedding_service
from app.db.queries import semantic_search
from app.db.neo4j_client import get_driver
from app.config import settings

SCHEMA_SYSTEM_PROMPT = """You are a Neo4j Cypher expert. Generate READ-ONLY Cypher queries for a Pakistani politicians database.

Schema:
- (Politician {id, name, born, bio, embedding})
- (Party {id, name, abbreviation})
- (Position {id, title, level, branch})
- (Event {id, name, event_date, event_type})
- (Source {id, url, scraped_at})

Relationships:
- (Politician)-[:MEMBER_OF {from_date, to_date, role}]->(Party)
- (Politician)-[:HELD_POSITION {from_date, to_date, constituency}]->(Position)
- (Politician)-[:ALLIED_WITH]->(Politician)
- (Politician)-[:OPPOSED_TO]->(Politician)
- (Politician)-[:RELATED_TO]->(Politician)
- (Politician)-[:SOURCED_FROM]->(Source)

Return ONLY the Cypher query, no explanation."""


async def cypher_query_node(state: AgentState) -> dict:
    query = state.get("query", "")
    if not query:
        return {"query_results": [], "error": "No query provided"}

    # Try semantic search first
    try:
        embedding = await embedding_service.embed_text(query)
        driver = await get_driver()
        results = await semantic_search(driver, embedding, top_k=5)
        if results:
            return {"query_results": results, "error": None}
    except Exception:
        pass

    # Fall back to LLM-generated Cypher
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
    response = await llm.ainvoke([
        SystemMessage(content=SCHEMA_SYSTEM_PROMPT),
        HumanMessage(content=f"Generate a Cypher query for: {query}")
    ])

    cypher = response.content.strip()
    if cypher.startswith("```"):
        cypher = cypher.split("```")[1]
        if cypher.startswith("cypher"):
            cypher = cypher[6:]
        cypher = cypher.strip()

    try:
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(cypher)
            rows = [dict(record) async for record in result]
        return {"query_results": rows, "error": None}
    except Exception as e:
        return {"query_results": [], "error": f"Query execution failed: {e}"}


async def format_results_node(state: AgentState) -> dict:
    results = state.get("query_results", [])
    query = state.get("query", "")

    if not results:
        return {"final_answer": "No results found for your query."}

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
    response = await llm.ainvoke([
        SystemMessage(content="You are a helpful assistant. Summarize the database results in a clear, concise answer."),
        HumanMessage(content=f"Question: {query}\n\nDatabase results: {json.dumps(results, default=str)[:3000]}")
    ])

    return {"final_answer": response.content}
