from __future__ import annotations

import math
from collections import Counter
from typing import Iterable


def entropy(tags_window: list[list[str]]) -> float:
    # compute entropy over tag distribution in a window
    flat = [t for tags in tags_window for t in tags]
    if not flat:
        return 0.0
    c = Counter(flat)
    total = sum(c.values())
    H = 0.0
    for k, v in c.items():
        p = v / total
        H -= p * math.log(p + 1e-12)
    return float(H)


def creator_dominance(creators: list[str | None]) -> float:
    vals = [c for c in creators if c]
    if not vals:
        return 0.0
    c = Counter(vals)
    return float(max(c.values()) / len(vals))
