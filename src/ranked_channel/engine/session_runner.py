from __future__ import annotations

import asyncio
import secrets
from dataclasses import asdict
from typing import Any

from playwright.async_api import Page

from ranked_channel.config import settings
from ranked_channel.crawl.browser import launch_page, polite_sleep
from ranked_channel.crawl.extract_video_id import extract_video_identity
from ranked_channel.crawl.extract_tags import extract_tags
from ranked_channel.crawl.extract_related import extract_related, RelatedVideo
from ranked_channel.crawl.normalize import canonicalize_url
from ranked_channel.domain.models import Video, Candidate
from ranked_channel.domain.scoring import (
    sat_log1p, normalize01, sim_from_taste, diversity_penalty, novelty_bonus, combined_score,
)
from ranked_channel.domain.policy import softmax_sample
from ranked_channel.store.sqlite import Store
from ranked_channel.engine.player_url import make_player_url



class SessionEngine:
    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    async def _visit(self, page: Page, url: str) -> None:
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(settings.wait_after_load_ms)

    async def build_session(self, seed_url: str, n: int | None = None, profile: str = "discovery") -> dict[str, Any]:
        n = int(n or settings.default_session_len)
        seed_url = canonicalize_url(seed_url)

        session_id = secrets.token_hex(8)

        config = {
            "profile": profile,
            "w_related": settings.w_related,
            "w_sim": settings.w_sim,
            "w_div": settings.w_div,
            "w_novelty": settings.w_novelty,
            "temperature": settings.temperature,
            "diversity_window_k": settings.diversity_window_k,
            "sample_top_m": settings.sample_top_m,
        }
        self.store.create_session(session_id, seed_url, config)

        taste = self.store.get_taste()

        picked: list[str] = []
        recent_tag_sets: list[set[str]] = []
        candidate_map: dict[str, dict[str, Any]] = {}  # video_id -> info (url/title/tags/encoded_id)
        related_freq: dict[str, int] = {}  # video_id -> freq among explored from picked set

        async with launch_page() as page:
            current_url = seed_url
            current_id = None

            for idx in range(n):
                await self._visit(page, current_url)
                await polite_sleep()

                video = await extract_video_identity(page)
                if not video:
                    # Fallback: derive key from url (not ideal, but keeps session alive)
                    video = f"url:{canonicalize_url(current_url)}"
                video_id = video.video_id
                encoded_id = video.encoded_id
                tags = await extract_tags(page)
                title = None
                try:
                    title = (await page.title()) or None
                except Exception:
                    title = None

                # Persist current node + mark seen
                self.store.upsert_video(video_id, current_url, title, tags)
                self.store.incr_seen(video_id, 1)
                candidate_map.setdefault(video_id, {
                    "video_id": video_id,
                    "url": current_url,
                    "title": title,
                    "tags": tags,
                    "encoded_id": encoded_id,
                })
                if encoded_id:
                    candidate_map[video_id]["encoded_id"] = encoded_id

                # Add to session items with explain filled later
                picked.append(video_id)
                recent_tag_sets.append(set(tags))
                if len(recent_tag_sets) > settings.diversity_window_k:
                    recent_tag_sets.pop(0)

                # Extract related and update graph + candidate pool
                related = await extract_related(page, current_url)
                for rv in related:
                    to_url = rv.url
                    # For related nodes, we do not know id_video yet; use data-id if present, else url key.
                    to_id = rv.video_id or f"url:{to_url}"
                    candidate_map.setdefault(to_id, {
                        "video_id": to_id,
                        "url": to_url,
                        "title": rv.title,
                        "tags": [],  # will be filled when visited
                        "encoded_id": rv.eid,
                    })
                    if rv.eid:
                        candidate_map[to_id]["encoded_id"] = rv.eid
                    # graph edge weight
                    self.store.incr_edge(video_id, to_id, 1)
                    # freq count inside this session
                    related_freq[to_id] = related_freq.get(to_id, 0) + 1

                # Build candidate list excluding already picked
                candidates: list[Candidate] = []
                freq_vals = []
                temp_candidates = []
                for cid, info in candidate_map.items():
                    if cid in picked:
                        continue
                    freq = related_freq.get(cid, 0)
                    freq_vals.append(sat_log1p(freq))
                    temp_candidates.append((cid, info, freq))

                freq_norms = normalize01(freq_vals)
                for (cid, info, freq), fn in zip(temp_candidates, freq_norms):
                    # Tags may be empty if not visited; similarity uses taste only in that case.
                    ctags = info.get("tags") or []
                    sim = sim_from_taste(ctags, taste)
                    div = diversity_penalty(ctags, recent_tag_sets)
                    seen = self.store.get_seen_count(cid)
                    nov = novelty_bonus(seen)
                    score = combined_score(freq=freq, sim=sim, div=div, novelty=nov, freq_norm=fn)

                    candidates.append(Candidate(
                        video=Video(
                            video_id=cid,
                            encoded_id=info.get("encoded_id"),
                            url=info["url"],
                            title=info.get("title"),
                            tags=ctags,
                        ),
                        freq=freq, sim=sim, div=div, novelty=nov, score=score
                    ))

                # Explain for current item (based on what we know after scraping)
                explain = {
                    "picked_idx": idx,
                    "tags": tags,
                    "note": "Seed" if idx == 0 else "Chosen by policy",
                }
                self.store.add_session_item(session_id, idx, video_id, current_url, title, explain)

                if idx == n - 1:
                    break

                # Pick next
                if not candidates:
                    break

                nxt = softmax_sample(candidates)
                current_url = nxt.video.url
                current_id = nxt.video.video_id

        items = self.store.list_session_items(session_id)
        return {
        "video_id": video.video_id,
        "url": video.url,                       # canonical / shareable page URL
        "play_url": make_player_url(video),     # iframe-friendly URL
        "title": video.title,
        "tags": video.tags,
        "score": explain.score,
        "freq": explain.freq,
        "sim": explain.sim,
        "div": explain.div,
        "novelty": explain.novelty,
    }


