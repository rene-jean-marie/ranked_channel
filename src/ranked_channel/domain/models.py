from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Video:
    video_id: str
    url: str
    title: Optional[str]
    tags: list[str]


@dataclass
class Candidate:
    video: Video
    freq: int
    sim: float
    div: float
    novelty: float
    score: float
