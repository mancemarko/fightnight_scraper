"""Curated fight cards: suggestions and event lookup for a query."""
from __future__ import annotations

import json
from pathlib import Path

from .classify import DATA_DIR
from .names import Query, token_hit, tokens


def load_events(path: Path | None = None) -> list[dict]:
    return json.loads((path or DATA_DIR / "events.json").read_text(encoding="utf-8"))["events"]


def suggestions(events: list[dict]) -> list[dict]:
    out = []
    for event in events:
        if event.get("suggested"):
            a, b = (f["name"] for f in event["fighters"])
            out.append({"query": f"{a} vs {b}", "title": event["title"], "date": event["date"]})
    return out


def match_event(query: Query, events: list[dict]) -> dict | None:
    """The first event whose fighters' surnames are all present in the query."""
    query_tokens = [t for side in query.sides for t in side]
    for event in events:
        surnames = [tokens(f["name"])[-1] for f in event["fighters"]]
        if all(token_hit(s, query_tokens) for s in surnames):
            return event
    return None
