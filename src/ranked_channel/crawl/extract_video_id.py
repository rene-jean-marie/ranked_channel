from __future__ import annotations

import re
from playwright.async_api import Page

_ID_VIDEO_RE = re.compile(r'"id_video"\s*:\s*(\d+)')


async def extract_id_video(page: Page) -> str | None:
    # Pull all script contents and look for the configuration blob containing id_video.
    scripts = await page.locator("script").all_inner_texts()
    for s in scripts:
        if '"id_video"' not in s:
            continue
        m = _ID_VIDEO_RE.search(s)
        if m:
            return m.group(1)
    return None
