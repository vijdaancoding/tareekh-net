from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import re


url = "https://en.wikipedia.org/wiki/Muhammad_Ali_Jinnah"

async def scrape_wikipedia(url: str) -> tuple[str, str]:

    print(f"\n{'='*60}")
    print(f"  SCRAPING: {url}")
    print(f"{'='*60}")

    config = CrawlerRunConfig(
        # Return clean markdown, stripping nav/footer/tables
        markdown_generator=DefaultMarkdownGenerator(
            options={
                "ignore_links": False,
                "body_width":   0,      # no line wrapping
            }
        ),
        # Wikipedia-specific: exclude sidebar, footer, edit buttons
        excluded_selector="[id='toc'], .mw-editsection, #catlinks, .navbox, #footer",
        word_count_threshold=10,        # skip tiny DOM fragments
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

    markdown = result.markdown.raw_markdown
    print(f"'{title}' — {len(markdown):,} characters of markdown\n")
    return title, markdown




