from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, Page

from ranked_channel.config import settings


@asynccontextmanager
async def launch_page():
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=settings.headless)
        context = await browser.new_context()
        page: Page = await context.new_page()
        page.set_default_navigation_timeout(settings.navigation_timeout_ms)
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


async def polite_sleep():
    await asyncio.sleep(settings.throttle_ms / 1000)
