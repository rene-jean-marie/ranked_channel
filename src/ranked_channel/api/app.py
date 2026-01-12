from __future__ import annotations

from urllib.parse import urlparse
from urllib.request import Request, urlopen

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

def _is_allowed_proxy_url(target_url: str) -> bool:
    parsed = urlparse(target_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host.endswith("xnxx.com"):
        return False
    if not parsed.path.startswith("/embedframe/") and not parsed.path.startswith("/embed/"):
        return False
    return True


@app.get("/proxy", response_class=HTMLResponse)
def proxy_xnxx(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    if not _is_allowed_proxy_url(url):
        raise HTTPException(status_code=400, detail="invalid proxy url")

    parsed = urlparse(url)
    base_href = f"{parsed.scheme}://{parsed.netloc}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as resp:
            html = resp.read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"proxy fetch failed: {exc}") from exc

    body = html.decode("utf-8", errors="replace")
    script = """
<script>
(() => {
  const sendEnded = () => {
    try {
      window.parent.postMessage({ message: "VideoEvent: Ended" }, "*");
    } catch (err) {
      // ignore
    }
  };
  const attach = () => {
    const video = document.querySelector("video");
    if (!video || video.dataset.postMessageBound) return false;
    video.dataset.postMessageBound = "true";
    video.addEventListener("ended", sendEnded);
    return true;
  };
  if (!attach()) {
    const observer = new MutationObserver(() => {
      if (attach()) observer.disconnect();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
</script>
""".strip()
    base_tag = f'<base href="{base_href}">'
    if "</head>" in body:
        body = body.replace("</head>", f"{base_tag}\n{script}\n</head>", 1)
    elif "</body>" in body:
        body = body.replace("</body>", f"{base_tag}\n{script}\n</body>", 1)
    else:
        body = f"{body}\n{base_tag}\n{script}"

    return HTMLResponse(content=body)


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
