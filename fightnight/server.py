"""Tiny stdlib HTTP server: serves web/ and a JSON API. No third-party web framework."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .classify import DATA_DIR
from .events import suggestions
from .search import SearchService

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_QUERY_LEN = 120
_STATIC_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8"}
_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' https://i.ytimg.com; "
        "connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def make_handler(service: SearchService, official_channels: list[str], web_dir: Path = WEB_DIR):
    class Handler(BaseHTTPRequestHandler):
        server_version = "fightnight"

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/api/suggestions":
                self._json(suggestions(service.events))
            elif url.path == "/api/channels":
                self._json(official_channels)
            elif url.path == "/api/search":
                query = parse_qs(url.query).get("q", [""])[0].strip()
                if not query or len(query) > MAX_QUERY_LEN:
                    self._json({"error": f"Enter 1-{MAX_QUERY_LEN} characters."}, HTTPStatus.BAD_REQUEST)
                else:
                    self._json(service.search(query))
            else:
                self._static(url.path)

        def _static(self, path: str):
            name = "index.html" if path == "/" else path.lstrip("/")
            file = (web_dir / name).resolve()
            if file.parent != web_dir.resolve() or file.suffix not in _STATIC_TYPES or not file.is_file():
                self._json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
                return
            self._send(HTTPStatus.OK, file.read_bytes(), _STATIC_TYPES[file.suffix])

        def _json(self, payload, status: HTTPStatus = HTTPStatus.OK):
            self._send(status, json.dumps(payload).encode(), "application/json", no_store=True)

        def _send(self, status: HTTPStatus, body: bytes, content_type: str, no_store: bool = False):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Security-Policy", _CSP)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if no_store:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # keep the console quiet; queries are not logged
            pass

    return Handler


def make_server(host: str, port: int, service: SearchService, official_channels: list[str]) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(service, official_channels))


def official_channel_names() -> list[str]:
    return json.loads((DATA_DIR / "official_channels.json").read_text(encoding="utf-8"))["channels"]
