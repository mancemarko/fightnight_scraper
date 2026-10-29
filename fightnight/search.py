"""Run a query across sources, classify and rank what comes back."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Lock
from typing import Protocol

from .classify import KIND_RANK, detect_kind, is_official, parse_duration
from .events import match_event
from .names import parse_query, query_variants, relevance, tokens
from .sources import SourceError

MAX_RESULTS = 60


class Source(Protocol):
    name: str

    def search(self, text: str) -> list[dict]: ...


class SearchService:
    def __init__(self, sources: list[Source], official_channels: frozenset[str], events: list[dict],
                 ttl: float = 600, clock=time.monotonic):
        self._sources = sources
        self._official = official_channels
        self.events = events
        self._ttl = ttl
        self._clock = clock
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = Lock()

    def search(self, raw_query: str) -> dict:
        query = parse_query(raw_query)
        if not query.sides:
            return self._payload(query, [], [])
        key = " ".join(tokens(raw_query))
        with self._lock:
            cached = self._cache.get(key)
        if cached and cached[0] > self._clock():
            return cached[1]

        variants = query_variants(query)
        jobs = [(source, variant) for source in self._sources for variant in variants]
        with ThreadPoolExecutor(max_workers=len(jobs) or 1) as pool:
            outcomes = list(pool.map(lambda job: self._run(*job), jobs))

        reports, results = [], {}
        for source in self._sources:
            mine = [o for (src, _), o in zip(jobs, outcomes) if src is source]
            errors = [o for o in mine if isinstance(o, SourceError)]
            videos = [v for o in mine if not isinstance(o, SourceError) for v in o]
            for video in videos:
                results.setdefault((source.name, video["id"]), self._build(query, source.name, video))
            reports.append({
                "name": source.name,
                "ok": len(errors) < len(mine),
                "error": str(errors[-1]) if errors else None,
                "count": len({v["id"] for v in videos}),
            })

        ranked = sorted(
            (r for r in results.values() if r["match"] != "none"),
            key=lambda r: (r["match"] != "full", not r["official"], KIND_RANK[r["kind"]], -r["score"]),
        )[:MAX_RESULTS]
        payload = self._payload(query, reports, ranked)
        if any(r["ok"] for r in reports):
            with self._lock:
                self._cache[key] = (self._clock() + self._ttl, payload)
        return payload

    def _payload(self, query, reports: list[dict], results: list[dict]) -> dict:
        return {
            "query": query.raw,
            "event": match_event(query, self.events),
            "sources": reports,
            "results": results,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    @staticmethod
    def _run(source: Source, text: str):
        try:
            return source.search(text)
        except SourceError as exc:
            return exc

    def _build(self, query, source_name: str, video: dict) -> dict:
        match, score = relevance(query, video["title"])
        return {
            "id": video["id"],
            "url": video["url"],
            "thumbnail": video["thumbnail"],
            "title": video["title"],
            "channel": video["channel"],
            "platform": source_name,
            "cost": "Free",
            "official": is_official(video["channel"], video["verified"], self._official),
            "verified": video["verified"],
            "kind": detect_kind(
                video["title"], live=video["live"], upcoming=video["upcoming"],
                duration_seconds=parse_duration(video["duration"]),
            ),
            "match": match,
            "score": round(score, 3),
            "duration": video["duration"],
            "published": video["published"],
            "views": video["views"],
        }
