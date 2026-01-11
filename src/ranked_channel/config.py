from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RC_", env_file=".env", extra="ignore")

    # SQLite database path
    db_path: str = "ranked_channel.sqlite3"

    # Playwright
    headless: bool = True
    navigation_timeout_ms: int = 25_000
    wait_after_load_ms: int = 500
    throttle_ms: int = 400  # basic politeness throttle between page visits

    # Ranking knobs
    w_related: float = 0.45
    w_sim: float = 0.45
    w_div: float = 0.35
    w_novelty: float = 0.15

    diversity_window_k: int = 6

    # Exploration policy (softmax temperature)
    temperature: float = 0.85

    # Candidate management
    max_candidates: int = 250
    sample_top_m: int = 40  # restrict softmax to top-M to avoid junk tail

    # Session
    default_session_len: int = 30


settings = Settings()
