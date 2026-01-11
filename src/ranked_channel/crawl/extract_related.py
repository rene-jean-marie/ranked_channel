from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page

from ranked_channel.crawl.selectors import RELATED_CARD, RELATED_TITLE_LINK, RELATED_ANY_LINK
from ranked_channel.crawl.normalize import origin, canonicalize_url


@dataclass(frozen=True)
class RelatedVideo:
    url: str
    title: Optional[str]
    video_id: Optional[str]  # data-id if present
    eid: Optional[str]


async def extract_related(page: Page, base_url: str) -> list[RelatedVideo]:
    # Wait for related cards if present; otherwise return empty.
    cards = page.locator(RELATED_CARD)
    if await cards.count() == 0:
        return []

    base_origin = origin(base_url)
    results: list[RelatedVideo] = []
    seen: set[str] = set()

    count = await cards.count()
    for i in range(count):
        card = cards.nth(i)
        video_id = await card.get_attribute("data-id")
        eid = await card.get_attribute("data-eid")

        # Prefer the title link selector to avoid channel/uploader links.
        link = card.locator(RELATED_TITLE_LINK)
        href = None
        title = None
        if await link.count():
            href = await link.first.get_attribute("href")
            try:
                title = (await link.first.inner_text()).strip() or None
            except Exception:
                title = None

        if not href:
            # fallback: first anchor
            a = card.locator(RELATED_ANY_LINK)
            if await a.count():
                href = await a.first.get_attribute("href")

        if not href:
            continue

        if href.startswith("/"):
            url = base_origin + href
        else:
            url = href

        url = canonicalize_url(url)

        key = video_id or url or eid
        if not key or key in seen:
            continue
        seen.add(key)

        results.append(RelatedVideo(url=url, title=title, video_id=video_id, eid=eid))

    return results
