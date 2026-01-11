from __future__ import annotations

import math
import random
from typing import Sequence

from ranked_channel.config import settings
from ranked_channel.domain.models import Candidate


def softmax_sample(cands: list[Candidate]) -> Candidate:
    # Restrict to top-M to avoid sampling the junk tail.
    cands = sorted(cands, key=lambda c: c.score, reverse=True)[: settings.sample_top_m]
    if not cands:
        raise ValueError("No candidates to sample from")

    T = max(1e-6, settings.temperature)
    logits = [c.score / T for c in cands]
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    s = sum(exps)
    r = random.random() * s
    acc = 0.0
    for c, e in zip(cands, exps):
        acc += e
        if acc >= r:
            return c
    return cands[-1]
