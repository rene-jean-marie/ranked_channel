from urllib.parse import parse_qs, urlparse

def _extract_youtube_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "youtu.be" in host:
        return path.lstrip("/") or None

    if "youtube.com" in host:
        if path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if path.startswith("/embed/"):
            return path.split("/")[2] if len(path.split("/")) > 2 else None
        if path.startswith("/shorts/"):
            return path.split("/")[2] if len(path.split("/")) > 2 else None

    return None

def make_player_url(video) -> str:
    """
    Returns a URL that is suitable for playback in the web UI.
    Falls back to the normal page URL if no embed route is available.
    """
    host = (urlparse(video.url).netloc or "").lower()

    # XNXX: prefers embedframe/{encoded_id_video} for iframe playback
    if "xnxx.com" in host and getattr(video, "encoded_id", None):
        return f"https://www.xnxx.com/embedframe/{video.encoded_id}"

    youtube_id = _extract_youtube_id(video.url)
    if youtube_id:
        return f"https://www.youtube.com/embed/{youtube_id}"

    return video.url
