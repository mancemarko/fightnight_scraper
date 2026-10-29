import unittest
from pathlib import Path

import requests

from fightnight.sources import SourceError
from fightnight.sources.youtube import YouTubeSource, extract_initial_data, parse_results

# SYNTHETIC page shaped like YouTube's ytInitialData; it is not scraped from the real site.
FIXTURE = (Path(__file__).parent / "fixtures" / "youtube_results_synthetic.html").read_text()


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.videos = {v["id"]: v for v in parse_results(FIXTURE)}

    def test_order_and_invalid_ids_dropped(self):
        self.assertEqual(list(self.videos), ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc", "ddddddddddd", "eeeeeeeeeee"])

    def test_fields(self):
        v = self.videos["aaaaaaaaaaa"]
        self.assertEqual(v["title"], "Muzamiru Kakande vs Tiago Muxanga | FULL FIGHT")
        self.assertEqual(v["channel"], "DAZN Boxing")
        self.assertTrue(v["verified"])
        self.assertEqual(v["duration"], "42:10")
        self.assertEqual(v["url"], "https://www.youtube.com/watch?v=aaaaaaaaaaa")
        self.assertEqual(v["thumbnail"], "https://i.ytimg.com/vi/aaaaaaaaaaa/mqdefault.jpg")

    def test_flags(self):
        self.assertFalse(self.videos["bbbbbbbbbbb"]["verified"])
        self.assertTrue(self.videos["ddddddddddd"]["live"])
        self.assertFalse(self.videos["aaaaaaaaaaa"]["live"])
        self.assertTrue(self.videos["eeeeeeeeeee"]["upcoming"])

    def test_missing_data_raises(self):
        with self.assertRaises(SourceError):
            extract_initial_data("<html>consent page</html>")
        with self.assertRaises(SourceError):
            extract_initial_data("var ytInitialData = {broken;")


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class FakeResponse:
    def __init__(self, text="", status_code=200, url="https://www.youtube.com/results"):
        self.text, self.status_code, self.url = text, status_code, url


class SourceTests(unittest.TestCase):
    def test_search_builds_encoded_url_and_parses(self):
        session = FakeSession(FakeResponse(FIXTURE))
        videos = YouTubeSource(session).search("kakande vs muxanga & more")
        self.assertEqual(len(videos), 5)
        self.assertIn("search_query=kakande+vs+muxanga+%26+more", session.calls[0][0])

    def test_network_error(self):
        with self.assertRaisesRegex(SourceError, "Could not reach YouTube"):
            YouTubeSource(FakeSession(error=requests.ConnectionError())).search("x")

    def test_http_error(self):
        with self.assertRaisesRegex(SourceError, "HTTP 429"):
            YouTubeSource(FakeSession(FakeResponse(status_code=429))).search("x")

    def test_consent_redirect(self):
        resp = FakeResponse(url="https://consent.youtube.com/m?continue=...")
        with self.assertRaisesRegex(SourceError, "consent"):
            YouTubeSource(FakeSession(resp)).search("x")


if __name__ == "__main__":
    unittest.main()
