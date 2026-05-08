import asyncio
from app.agents.state import AgentState, ScrapedSource
from scraping.crawler import scrape_wikipedia


def _log(msg: str) -> None:
    print(f"  [WEB SCRAPER] {msg}", flush=True)


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


async def web_scraper_node(state: AgentState) -> dict:
    sources: list[ScrapedSource] = []

    # Scrape primary URL
    try:
        title, markdown, page_links = await scrape_wikipedia(state["target_url"])
        sources.append(ScrapedSource(url=state["target_url"], title=title, markdown=markdown))
    except Exception as e:
        _log(f"ERROR: Primary scrape failed: {e}")
        return {"error": f"Primary scrape failed: {e}", "scraped_sources": sources}

    # Use actual page links — no LLM URL hallucination risk
    secondary_urls = [
        url for url in page_links
        if _is_valid_wikipedia_article(url) and url != state["target_url"]
    ][:2]
    _log(f"Scraping {len(secondary_urls)} related article(s) in parallel")

    if secondary_urls:
        results = await asyncio.gather(
            *[scrape_wikipedia(url) for url in secondary_urls],
            return_exceptions=True,
        )
        for url, res in zip(secondary_urls, results):
            if isinstance(res, Exception):
                _log(f"Failed to scrape {url}: {res}")
            else:
                rel_title, rel_markdown, _ = res
                sources.append(ScrapedSource(url=url, title=rel_title, markdown=rel_markdown))

    _log(f"Done — {len(sources)} source(s) collected")
    return {"scraped_sources": sources, "error": None}
