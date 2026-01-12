from urllib.parse import urlparse

def make_player_url(video) -> str:
    """
    Returns a URL that is suitable for playback in the web UI.
    Falls back to the normal page URL if no embed route is available.
    """
    host = (urlparse(video.url).netloc or "").lower()

    # XNXX: prefers embedframe/{encoded_id_video} for iframe playback
    if "xnxx.com" in host and getattr(video, "encoded_id", None):
        return f"https://www.xnxx.com/embedframe/{video.encoded_id}"

    return video.url
