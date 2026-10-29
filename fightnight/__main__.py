"""CLI: ``python -m fightnight serve`` or ``python -m fightnight search "A vs B"``."""
from __future__ import annotations

import argparse

from .classify import load_official_channels
from .events import load_events
from .search import SearchService
from .server import make_server, official_channel_names
from .sources.youtube import YouTubeSource


def build_service() -> SearchService:
    return SearchService([YouTubeSource()], load_official_channels(), load_events())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fightnight", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the web app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    search = sub.add_parser("search", help="search from the terminal")
    search.add_argument("query")
    args = parser.parse_args(argv)

    service = build_service()
    if args.command == "serve":
        server = make_server(args.host, args.port, service, official_channel_names())
        print(f"Fightnight running at http://{args.host}:{args.port}  (Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    payload = service.search(args.query)
    for report in payload["sources"]:
        status = f"{report['count']} videos" if report["ok"] else f"FAILED: {report['error']}"
        print(f"[{report['name']}] {status}")
    for r in payload["results"]:
        tag = "OFFICIAL" if r["official"] else "unverified"
        print(f"{tag:10} {r['kind']:10} {r['title']}  ({r['channel']})\n{'':21}{r['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
