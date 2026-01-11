from __future__ import annotations

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "feature", "si",
}

def origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"

def canonicalize_url(url: str) -> str:
    p = urlparse(url)
    # Drop fragments
    fragment = ""
    # Remove common tracking query params
    qs = [(k, v) for (k, v) in parse_qsl(p.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    query = urlencode(qs)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, query, fragment))
