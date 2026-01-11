from __future__ import annotations

import math
from typing import Iterable

from ranked_channel.config import settings


def sat_log1p(x: float) -> float:
    return math.log1p(max(0.0, x))


def normalize01(values: list[float]) -> list[float]:
    if not values:
        return []
    mn = min(values)
    mx = max(values)
    if mx - mn < 1e-9:
        return [0.0 for _ in values]
    return [(v - mn) / (mx - mn) for v in values]


def sim_from_taste(tags: list[str], taste: dict[str, float]) -> float:
    # Lightweight “centroid” similarity: sum weights of matching tags, normalized.
    if not tags or not taste:
        return 0.0
    total = sum(max(0.0, w) for w in taste.values())
    if total <= 1e-9:
        return 0.0
    return float(sum(max(0.0, taste.get(t, 0.0)) for t in tags) / total)


def diversity_penalty(tags: list[str], recent_tag_sets: list[set[str]]) -> float:
    # MMR-like: penalize if candidate overlaps heavily with recent items.
    if not tags or not recent_tag_sets:
        return 0.0
    s = set(tags)
    best = 0.0
    for r in recent_tag_sets:
        if not r:
            continue
        inter = len(s & r)
        union = len(s | r)
        if union == 0:
            continue
        j = inter / union
        if j > best:
            best = j
    return float(best)


def novelty_bonus(seen_count: int) -> float:
    # Higher when under-explored; decays as seen increases.
    return float(1.0 / (1.0 + max(0, seen_count)))


def combined_score(freq: int, sim: float, div: float, novelty: float,
                   freq_norm: float) -> float:
    # freq_norm is already normalized in [0,1]
    return (
        settings.w_related * freq_norm
        + settings.w_sim * sim
        - settings.w_div * div
        + settings.w_novelty * novelty
    )
