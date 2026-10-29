import json
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import quote

from fightnight.classify import load_official_channels
from fightnight.events import load_events
from fightnight.search import SearchService
from fightnight.server import MAX_QUERY_LEN, make_server, official_channel_names
from tests.test_search import PAGES, StubSource


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        service = SearchService([StubSource(PAGES)], load_official_channels(), load_events())
        cls.server = make_server("127.0.0.1", 0, service, official_channel_names())
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as err:
            return err.code, err.headers, err.read()

    def test_pages_are_served(self):
        for path, marker in (("/", b"Searcher"), ("/app.js", b"runSearch"), ("/style.css", b"--accent")):
            status, headers, body = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(marker, body)

    def test_security_headers(self):
        _, headers, _ = self.get("/")
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_suggestions_has_only_the_one_fight(self):
        _, _, body = self.get("/api/suggestions")
        self.assertEqual([s["query"] for s in json.loads(body)], ["Muzamiru Kakande vs Tiago Muxanga"])

    def test_channels(self):
        _, _, body = self.get("/api/channels")
        self.assertIn("DAZN Boxing", json.loads(body))

    def test_search(self):
        status, headers, body = self.get("/api/search?q=" + quote("Muzamiru Kakande vs Tiago Muxanga"))
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(body)["results"][0]["id"], "ddddddddddd")

    def test_bad_queries_are_rejected(self):
        self.assertEqual(self.get("/api/search")[0], 400)
        self.assertEqual(self.get("/api/search?q=%20%20")[0], 400)
        self.assertEqual(self.get("/api/search?q=" + "a" * (MAX_QUERY_LEN + 1))[0], 400)

    def test_path_traversal_and_other_files_are_not_served(self):
        for path in ("/../fightnight/server.py", "/%2e%2e/README.md", "/..%2fREADME.md",
                     "/nope.js", "/../../etc/passwd", "/sources/x.js"):
            self.assertEqual(self.get(path)[0], 404, path)


if __name__ == "__main__":
    unittest.main()
