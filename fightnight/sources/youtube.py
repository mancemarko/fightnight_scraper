"""YouTube search by scraping the public results page (free, no API key)."""
from __future__ import annotations

import json
import re
from typing import Iterator
from urllib.parse import quote_plus

import requests

from . import SourceError

SEARCH_URL = "https://www.youtube.com/results?search_query={}&hl=en"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    # Skips the EU cookie-consent interstitial.
    "Cookie": "CONSENT=YES+cb; SOCS=CAI",
}
_INITIAL_DATA = re.compile(r'ytInitialData(?:"\])?\s*=\s*')
_VIDEO_ID = re.compile(r"^[\w-]{11}$")


def _text(node: dict | None) -> str:
    if not node:
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    return "".join(run.get("text", "") for run in node.get("runs", []))


def extract_initial_data(html: str) -> dict:
    match = _INITIAL_DATA.search(html)
    if not match:
        raise SourceError("YouTube returned a page without search data (consent page or layout change).")
    try:
        data, _ = json.JSONDecoder().raw_decode(html, match.end())
    except json.JSONDecodeError as exc:
        raise SourceError("Could not read YouTube's search data (layout change).") from exc
    return data


def _video_renderers(node) -> Iterator[dict]:
    """Yield every videoRenderer in page order."""
    if isinstance(node, dict):
        renderer = node.get("videoRenderer")
        if isinstance(renderer, dict):
            yield renderer
            return
        for value in node.values():
            yield from _video_renderers(value)
    elif isinstance(node, list):
        for item in node:
            yield from _video_renderers(item)


def _parse_video(renderer: dict) -> dict | None:
    video_id = renderer.get("videoId", "")
    if not _VIDEO_ID.match(video_id):
        return None
    owner = renderer.get("ownerText", {})
    badges = renderer.get("badges", [])
    overlays = renderer.get("thumbnailOverlays", [])
    live = any("LIVE_NOW" in b.get("metadataBadgeRenderer", {}).get("style", "") for b in badges) or any(
        o.get("thumbnailOverlayTimeStatusRenderer", {}).get("style") == "LIVE" for o in overlays
    )
    verified = any(
        "VERIFIED" in b.get("metadataBadgeRenderer", {}).get("style", "")
        for b in renderer.get("ownerBadges", [])
    )
    return {
        "id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
        "title": _text(renderer.get("title")),
        "channel": _text(owner),
        "verified": verified,
        "live": live,
        "upcoming": "upcomingEventData" in renderer,
        "duration": _text(renderer.get("lengthText")),
        "published": _text(renderer.get("publishedTimeText")),
        "views": _text(renderer.get("viewCountText")),
    }


def parse_results(html: str) -> list[dict]:
    videos = (_parse_video(r) for r in _video_renderers(extract_initial_data(html)))
    return [v for v in videos if v]


class YouTubeSource:
    name = "YouTube"

    def __init__(self, session: requests.Session | None = None, timeout: tuple[int, int] = (5, 10)):
        self._session = session or requests.Session()
        self._timeout = timeout

    def search(self, text: str) -> list[dict]:
        try:
            response = self._session.get(SEARCH_URL.format(quote_plus(text)), headers=_HEADERS, timeout=self._timeout)
        except requests.RequestException as exc:
            raise SourceError(f"Could not reach YouTube ({type(exc).__name__}).") from exc
        if "consent.youtube.com" in response.url:
            raise SourceError("YouTube asked for cookie consent instead of showing results.")
        if response.status_code != 200:
            raise SourceError(f"YouTube answered HTTP {response.status_code}.")
        return parse_results(response.text)
