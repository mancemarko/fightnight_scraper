import unittest

from fightnight.classify import load_official_channels
from fightnight.events import load_events
from fightnight.search import SearchService
from fightnight.sources import SourceError


def video(vid, title, channel="Some Channel", verified=False, duration="", live=False, upcoming=False):
    return {
        "id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
        "thumbnail": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", "title": title, "channel": channel,
        "verified": verified, "live": live, "upcoming": upcoming, "duration": duration,
        "published": "", "views": "",
    }


class StubSource:
    name = "Stub"

    def __init__(self, pages=None, error=None, fail_on=None):
        self.pages, self.error, self.fail_on, self.calls = pages or [], error, fail_on, []

    def search(self, text):
        self.calls.append(text)
        if self.error or (self.fail_on and self.fail_on in text):
            raise SourceError(self.error or "boom")
        return list(self.pages)


PAGES = [
    video("bbbbbbbbbbb", "KAKANDE vs MUXANGA highlights", "Fan Channel", duration="6:00"),
    video("ccccccccccc", "Tiago Muxanga wins IBO title", "Boxing News", True, "3:00"),
    video("aaaaaaaaaaa", "Kakande vs Muxanga FULL FIGHT", "DAZN Boxing", True, "42:00"),
    video("zzzzzzzzzzz", "Fury vs Usyk full fight", "DAZN Boxing", True, "50:00"),
    video("ddddddddddd", "Kakande vs Muxanga", "Top Tier Boxing", True, live=True),
]
QUERY = "Muzamiru Kakande vs Tiago Muxanga"


def service(source, **kw):
    return SearchService([source], load_official_channels(), load_events(), **kw)


class SearchTests(unittest.TestCase):
    def test_ranking_filtering_and_dedupe(self):
        source = StubSource(PAGES)
        payload = service(source).search(QUERY)
        ids = [r["id"] for r in payload["results"]]
        # exact matches first (official live, official full fight, unverified highlights), then the
        # one-fighter video; the unrelated Fury video is dropped and nothing repeats across variants
        self.assertEqual(ids, ["ddddddddddd", "aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"])
        by_id = {r["id"]: r for r in payload["results"]}
        self.assertTrue(by_id["aaaaaaaaaaa"]["official"])
        self.assertFalse(by_id["bbbbbbbbbbb"]["official"])
        self.assertFalse(by_id["ccccccccccc"]["official"])  # verified, but "Boxing News" is not on the list
        self.assertEqual(by_id["ccccccccccc"]["match"], "partial")
        self.assertEqual(by_id["bbbbbbbbbbb"]["kind"], "highlights")
        self.assertTrue(all(r["cost"] == "Free" for r in payload["results"]))
        self.assertEqual(len(source.calls), 3)

    def test_event_attached_for_the_suggested_fight(self):
        payload = service(StubSource(PAGES)).search(QUERY)
        self.assertEqual(payload["event"]["id"], "kakande-muxanga-2026-10-25")

    def test_failure_is_reported_not_hidden(self):
        payload = service(StubSource(error="HTTP 403")).search(QUERY)
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["sources"], [{"name": "Stub", "ok": False, "error": "HTTP 403", "count": 0}])

    def test_partial_failure_keeps_results_and_reports_error(self):
        payload = service(StubSource(PAGES, fail_on="highlights")).search(QUERY)
        report = payload["sources"][0]
        self.assertTrue(report["ok"])
        self.assertEqual(report["error"], "boom")
        self.assertTrue(payload["results"])

    def test_successful_searches_are_cached(self):
        source = StubSource(PAGES)
        svc = service(source)
        first = svc.search(QUERY)
        calls = len(source.calls)
        self.assertIs(svc.search("muzamiru   KAKANDE vs tiago muxanga"), first)
        self.assertEqual(len(source.calls), calls)

    def test_cache_expires(self):
        now = [0.0]
        source = StubSource(PAGES)
        svc = service(source, ttl=10, clock=lambda: now[0])
        svc.search(QUERY)
        now[0] = 11
        svc.search(QUERY)
        self.assertEqual(len(source.calls), 6)

    def test_failures_are_not_cached(self):
        source = StubSource(error="down")
        svc = service(source)
        svc.search(QUERY)
        svc.search(QUERY)
        self.assertEqual(len(source.calls), 6)

    def test_query_without_names_skips_the_network(self):
        source = StubSource(PAGES)
        payload = service(source).search("boxing live stream")
        self.assertEqual(payload["results"], [])
        self.assertEqual(source.calls, [])


if __name__ == "__main__":
    unittest.main()
