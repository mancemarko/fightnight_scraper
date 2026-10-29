# Fightnight

Search for a boxing fight and find **free, official** streams, replays and highlights.

Everything is free: no paid APIs, no accounts, no ads. It scrapes YouTube's public search page, runs on the
Python standard library plus `requests`, and the web UI has no external dependencies.

## Run it

```bash
pip install -r requirements.txt
python -m fightnight serve            # http://127.0.0.1:8000
```

Or search from the terminal:

```bash
python -m fightnight search "Muzamiru Kakande vs Tiago Muxanga"
```

Run the tests:

```bash
python -m unittest discover -s tests -t .
```

## How it decides what to show

| Section | Meaning |
| --- | --- |
| **Official free streams and replays** | Channel name is in `fightnight/data/official_channels.json` **and** YouTube shows its verified badge. |
| **Uploads from unverified channels** | Mentions both fighters but the uploader isn't verified as official. Collapsed, with a warning. |
| **Related videos** | Mentions only one of the two fighters. Collapsed. |

Paid services (e.g. DAZN) appear on the fight card for context and are labelled *Subscription*; they are never
listed as free options. Pirate restreaming sites are not searched. Fightnight only links to videos on their
original platform and never hosts or restreams anything.

If a source can't be reached, the page says **"Search incomplete"** rather than showing an empty result as if nothing exists.

## Customising

- **Suggestions and fight cards:** `fightnight/data/events.json`. Events with `"suggested": true` show as chips on the Searcher tab.
- **Trusted channels:** `fightnight/data/official_channels.json` (exact channel names).
- **More sources:** add a class in `fightnight/sources/` with a `name` and a `search(text) -> list[dict]` method (see `sources/youtube.py` for the dict shape), then add it in `build_service()` in `fightnight/__main__.py`.

## Limitations

- The YouTube scraper reads the page's embedded JSON, which YouTube can change without notice. When that happens the UI reports the failure and the parser in `fightnight/sources/youtube.py` needs updating.
- Search results are cached in memory for 10 minutes.
- What's available depends on your region and on what rights-holders choose to publish.
