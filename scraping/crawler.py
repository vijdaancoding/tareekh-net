from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import re


_BLOCKED_WIKI_PREFIXES = (
    "Wikipedia:", "Help:", "Talk:", "User:", "Special:",
    "File:", "Category:", "Portal:", "Template:", "List_of",
)


async def scrape_wikipedia(url: str) -> tuple[str, str, list[str]]:
    """Scrape a Wikipedia article.

    Returns (title, fit_markdown, related_wiki_links).
    related_wiki_links are filtered internal Wikipedia article URLs found on the page.
    """
    print(f"\n{'='*60}\n  SCRAPING: {url}\n{'='*60}")

    config = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.45, threshold_type="fixed"),
            options={"ignore_links": False, "body_width": 0},
        ),
        excluded_selector=(
            "[id='toc'], .mw-editsection, #catlinks, .navbox, #footer, "
            ".reflist, .references, .mw-references-wrap"
        ),
        word_count_threshold=15,
        verbose=False,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=config)

    if not result.success:
        raise RuntimeError(f"Crawl failed: {result.error_message}")

    # Extract article title from <h1>
    title = "Unknown"
    if result.html:
        m = re.search(r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>', result.html, re.S)
        if m:
            title = re.sub(r"<.*?>", "", m.group(1)).strip()

    # Prefer fit_markdown (content-filtered) — falls back to raw if filter yields nothing
    markdown = result.markdown.fit_markdown or result.markdown.raw_markdown

    # Extract related Wikipedia article links from the page (no LLM hallucination risk)
    related_links: list[str] = []
    if result.links:
        base = "https://en.wikipedia.org"
        seen = {url}
        for link in result.links.get("internal", []):
            href = link.get("href", "")
            if not href.startswith("/wiki/"):
                continue
            path = href.split("#")[0]
            article_title = path.removeprefix("/wiki/")
            if not article_title:
                continue
            if any(article_title.startswith(p) for p in _BLOCKED_WIKI_PREFIXES):
                continue
            full_url = base + path
            if full_url not in seen:
                seen.add(full_url)
                related_links.append(full_url)

    print(f"'{title}' — {len(markdown):,} chars, {len(related_links)} related links\n")
    return title, markdown, related_links
