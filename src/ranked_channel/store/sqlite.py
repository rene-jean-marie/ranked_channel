from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ranked_channel.config import settings


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            schema_path = Path(__file__).with_name("schema.sql")
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()

    # --- videos ---
    def upsert_video(self, video_id: str, url: str, title: str | None, tags: list[str]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO videos(video_id, url, title, tags_json, created_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(video_id) DO UPDATE SET
                  url=excluded.url,
                  title=COALESCE(excluded.title, videos.title),
                  tags_json=CASE WHEN excluded.tags_json IS NOT NULL AND excluded.tags_json != '[]' THEN excluded.tags_json ELSE videos.tags_json END
                """,
                (video_id, url, title, json.dumps(tags), utcnow()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["tags"] = json.loads(d.get("tags_json") or "[]")
            return d
        finally:
            conn.close()

    # --- edges / co-occurrence ---
    def incr_edge(self, from_id: str, to_id: str, inc: int = 1) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO edges(from_video_id, to_video_id, weight)
                VALUES(?,?,?)
                ON CONFLICT(from_video_id, to_video_id) DO UPDATE SET
                  weight = edges.weight + excluded.weight
                """,
                (from_id, to_id, inc),
            )
            conn.commit()
        finally:
            conn.close()

    def get_incoming_weight(self, to_id: str, from_ids: list[str]) -> int:
        if not from_ids:
            return 0
        conn = self._connect()
        try:
            q = f"SELECT COALESCE(SUM(weight),0) as s FROM edges WHERE to_video_id=? AND from_video_id IN ({','.join(['?']*len(from_ids))})"
            row = conn.execute(q, (to_id, *from_ids)).fetchone()
            return int(row["s"]) if row else 0
        finally:
            conn.close()

    # --- seen counts ---
    def incr_seen(self, video_id: str, inc: int = 1) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO video_seen(video_id, seen_count)
                VALUES(?,?)
                ON CONFLICT(video_id) DO UPDATE SET
                  seen_count = video_seen.seen_count + excluded.seen_count
                """,
                (video_id, inc),
            )
            conn.commit()
        finally:
            conn.close()

    def get_seen_count(self, video_id: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT seen_count FROM video_seen WHERE video_id=?", (video_id,)).fetchone()
            return int(row["seen_count"]) if row else 0
        finally:
            conn.close()

    # --- taste profile ---
    def get_taste(self) -> dict[str, float]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT tag, weight FROM taste_profile").fetchall()
            return {r["tag"]: float(r["weight"]) for r in rows}
        finally:
            conn.close()

    def bump_taste(self, tags: list[str], amount: float) -> None:
        if not tags:
            return
        conn = self._connect()
        try:
            for t in tags:
                conn.execute(
                    """
                    INSERT INTO taste_profile(tag, weight) VALUES(?,?)
                    ON CONFLICT(tag) DO UPDATE SET weight = taste_profile.weight + excluded.weight
                    """,
                    (t, amount),
                )
            conn.commit()
        finally:
            conn.close()

    # --- sessions ---
    def create_session(self, session_id: str, seed_url: str, config: dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO sessions(session_id, seed_url, created_at, config_json) VALUES(?,?,?,?)",
                (session_id, seed_url, utcnow(), json.dumps(config)),
            )
            conn.commit()
        finally:
            conn.close()

    def add_session_item(self, session_id: str, idx: int, video_id: str, url: str, title: str | None, explain: dict[str, Any]) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO session_items(session_id, idx, video_id, url, title, explain_json)
                VALUES(?,?,?,?,?,?)
                """,
                (session_id, idx, video_id, url, title, json.dumps(explain)),
            )
            conn.commit()
        finally:
            conn.close()

    def list_session_items(self, session_id: str) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT idx, video_id, url, title, explain_json FROM session_items WHERE session_id=? ORDER BY idx ASC",
                (session_id,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["explain"] = json.loads(d["explain_json"])
                out.append(d)
            return out
        finally:
            conn.close()

    def add_feedback(self, session_id: str, video_id: str, action: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO feedback(session_id, video_id, action, created_at) VALUES(?,?,?,?)",
                (session_id, video_id, action, utcnow()),
            )
            conn.commit()
        finally:
            conn.close()
