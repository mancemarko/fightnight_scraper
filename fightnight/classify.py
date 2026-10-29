"""Decide what kind of video a result is and whether its channel is a trusted rights-holder."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .names import tokens

DATA_DIR = Path(__file__).parent / "data"

# Lower rank sorts first.
KIND_RANK = {"live": 0, "upcoming": 1, "full": 2, "highlights": 3, "extra": 4, "other": 5}

_EXTRA = re.compile(
    r"weigh[\s-]?in|press conference|face[\s-]?off|ring ?walk|interview|preview|prediction|"
    r"reaction|breakdown|analysis|workout|training camp|behind the scenes|promo",
    re.IGNORECASE,
)
_HIGHLIGHTS = re.compile(r"highlights?|knockout|\bko\b|recap|best moments|round \d", re.IGNORECASE)
_FULL = re.compile(r"full (?:fight|event|show|card|replay)|\breplay\b|complete fight", re.IGNORECASE)
_FULL_MIN_SECONDS = 25 * 60


def parse_duration(text: str) -> int | None:
    """'1:02:03' -> 3723, '12:34' -> 754, anything else -> None."""
    parts = text.strip().split(":")
    if not text or not all(p.isdigit() for p in parts) or len(parts) > 3:
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds


def detect_kind(title: str, *, live: bool, upcoming: bool, duration_seconds: int | None) -> str:
    if live:
        return "live"
    if upcoming:
        return "upcoming"
    if _EXTRA.search(title):
        return "extra"
    if _HIGHLIGHTS.search(title):
        return "highlights"
    if _FULL.search(title) or (duration_seconds or 0) >= _FULL_MIN_SECONDS:
        return "full"
    return "other"


def load_official_channels(path: Path | None = None) -> frozenset[str]:
    data = json.loads((path or DATA_DIR / "official_channels.json").read_text(encoding="utf-8"))
    return frozenset(" ".join(tokens(name)) for name in data["channels"])


def is_official(channel: str, verified: bool, official_channels: frozenset[str]) -> bool:
    """Official = exact channel-name match AND YouTube's verified badge.

    The badge requirement stops look-alike channels (e.g. "DAZN Boxing") from passing on name alone.
    """
    return verified and " ".join(tokens(channel)) in official_channels
