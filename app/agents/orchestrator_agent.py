import json
import httpx
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings

ORCHESTRATOR_PROMPT = """You are a routing assistant for a Pakistani politicians knowledge base.

Classify the user message into exactly one intent and extract relevant fields.

Intents:
- "ingest"  — user wants to add / import / save a politician to the database
- "query"   — user wants information about a politician or politics
- "pending" — user asks about pending approvals or wants to approve/reject
- "general" — greeting or off-topic

Return ONLY a JSON object, no markdown fences:
{
  "intent": "ingest" | "query" | "pending" | "general",
  "politician_name": "<name if ingest intent, else null>",
  "question": "<the user question verbatim if query intent, else null>",
  "reply": "<short friendly message confirming what you are doing, 1 sentence>"
}"""


async def classify_intent(message: str) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
    response = await llm.ainvoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=message),
    ])
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


async def find_wikipedia_url(politician_name: str) -> str | None:
    """Search Wikipedia API for the best matching article URL."""
    query = f"{politician_name} Pakistani politician"
    headers = {"User-Agent": "tareekh-net/0.1 (https://github.com/tareekh-net; contact@example.com)"}
    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        resp = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3,
            },
        )
        resp.raise_for_status()
        if not resp.content:
            return None
        data = resp.json()
        results = data.get("query", {}).get("search", [])
        if not results:
            return None
        title = results[0]["title"].replace(" ", "_")
        return f"https://en.wikipedia.org/wiki/{title}"
