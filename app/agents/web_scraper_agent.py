import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState, ScrapedSource
from scraping.crawler import scrape_wikipedia
from app.config import settings


def _log(msg: str) -> None:
    print(f"  [WEB SCRAPER] {msg}", flush=True)


async def web_scraper_node(state: AgentState) -> dict:
    sources: list[ScrapedSource] = []

    # Scrape primary URL
    try:
        title, markdown = await scrape_wikipedia(state["target_url"])
        sources.append(ScrapedSource(url=state["target_url"], title=title, markdown=markdown))
    except Exception as e:
        _log(f"ERROR: Primary scrape failed: {e}")
        return {"error": f"Primary scrape failed: {e}", "scraped_sources": sources}

    _log(f"Asking LLM for related Wikipedia articles...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.google_api_key)
    excerpt = sources[0]["markdown"][:3000]
    response = await llm.ainvoke([
        SystemMessage(content="You are a research assistant. Extract 2-3 related Wikipedia article URLs from the provided markdown. Return a JSON array of URLs. Only return the JSON array, nothing else."),
        HumanMessage(content=f"Find 2-3 related Wikipedia URLs from this article about {title}:\n\n{excerpt}")
    ])

    related_urls = []
    try:
        text = response.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        related_urls = json.loads(text)
        if not isinstance(related_urls, list):
            related_urls = []
    except Exception:
        related_urls = []

    _log(f"LLM suggested {len(related_urls)} related URL(s): {related_urls}")

    # Scrape related URLs (up to 2)
    scraped_secondary = 0
    for url in related_urls[:2]:
        if not _is_valid_wikipedia_article(url):
            _log(f"Skipping invalid/non-article URL: {url}")
            continue
        try:
            rel_title, rel_markdown = await scrape_wikipedia(url)
            sources.append(ScrapedSource(url=url, title=rel_title, markdown=rel_markdown))
            scraped_secondary += 1
        except Exception as e:
            _log(f"Failed to scrape {url}: {e}")
            continue

    _log(f"Done — {len(sources)} source(s) collected ({scraped_secondary} secondary)")
    return {"scraped_sources": sources, "error": None}


# Wikipedia namespaces and non-article paths to reject
_BLOCKED_PREFIXES = (
    "Wikipedia:", "Help:", "Talk:", "User:", "Special:",
    "File:", "Category:", "Portal:", "Template:",
)

def _is_valid_wikipedia_article(url: str) -> bool:
    if not isinstance(url, str):
        return False
    if not url.startswith("https://en.wikipedia.org/wiki/"):
        return False
    title = url.removeprefix("https://en.wikipedia.org/wiki/")
    if not title or title == "Main_Page":
        return False
    if any(title.startswith(prefix) for prefix in _BLOCKED_PREFIXES):
        return False
    return True
