from __future__ import annotations

from playwright.async_api import Page
from ranked_channel.crawl.selectors import TAGS


async def extract_tags(page: Page) -> list[str]:
    # Best-effort: if tags selector doesn't exist, return [].
    loc = page.locator(TAGS)
    if await loc.count() == 0:
        return []
    tags = await loc.all_inner_texts()
    tags = [t.strip().lower() for t in tags if t and t.strip()]

    # de-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out
