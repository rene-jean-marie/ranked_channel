from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ranked_channel.engine.session_runner import SessionEngine
from ranked_channel.store.sqlite import Store

app = FastAPI(title="ranked-channel")
store = Store()
engine = SessionEngine(store=store)

# Mount static web UI
app.mount("/static", StaticFiles(directory="web", html=False), name="static")


class FeedbackIn(BaseModel):
    session_id: str
    video_id: str
    action: str  # "like" | "skip" | "block"


@app.get("/", response_class=HTMLResponse)
def root():
    # Serve the minimal UI
    return FileResponse("web/index.html")


@app.get("/session")
async def get_session(seed_url: str, n: int = 30, profile: str = "discovery"):
    if not seed_url:
        raise HTTPException(status_code=400, detail="seed_url required")
    session = await engine.build_session(seed_url=seed_url, n=n, profile=profile)
    return session


@app.post("/feedback")
def post_feedback(fb: FeedbackIn):
    action = fb.action.lower().strip()
    if action not in {"like", "skip", "block"}:
        raise HTTPException(status_code=400, detail="action must be like|skip|block")

    store.add_feedback(fb.session_id, fb.video_id, action)

    # Update taste profile based on feedback.
    v = store.get_video(fb.video_id)
    tags = (v or {}).get("tags", [])

    if action == "like":
        store.bump_taste(tags, amount=1.0)
    elif action == "skip":
        store.bump_taste(tags, amount=-0.25)
    elif action == "block":
        store.bump_taste(tags, amount=-1.0)

    return {"ok": True}
