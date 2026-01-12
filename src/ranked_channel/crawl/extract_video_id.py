import re
from dataclasses import dataclass
from typing import Optional
from playwright.async_api import Page

# Regex that tolerates whitespace and different quoting.
RE_ID_VIDEO = re.compile(r'"id_video"\s*:\s*(\d+)')
RE_ENCODED = re.compile(r'"encoded_id_video"\s*:\s*"([^"]+)"')


@dataclass(frozen=True)
class VideoIdentity:
    video_id: str
    encoded_id: Optional[str] = None


async def extract_video_identity(page: Page) -> Optional[VideoIdentity]:
    scripts = await page.locator("script").all_inner_texts()

    for s in scripts:
        if "id_video" not in s:
            continue

        m_id = RE_ID_VIDEO.search(s)
        if not m_id:
            continue

        video_id = m_id.group(1)

        m_enc = RE_ENCODED.search(s)
        encoded_id = m_enc.group(1) if m_enc else None

        return VideoIdentity(video_id=video_id, encoded_id=encoded_id)

    return None
