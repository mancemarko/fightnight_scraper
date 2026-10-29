"""Query parsing and fuzzy fighter-name matching."""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

_VS = re.compile(r"\s+(?:vs\.?|v\.?|versus)\s+", re.IGNORECASE)
_NOISE = frozenset(
    {"vs", "v", "versus", "boxing", "fight", "full", "live", "stream", "free",
     "watch", "replay", "highlights", "the", "and"}
)
_FUZZY_CUTOFF = 0.84
_MIN_FUZZY_LEN = 4


def tokens(text: str) -> list[str]:
    """Lowercase, accent-stripped alphanumeric words."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", stripped.lower()).split()


@dataclass(frozen=True)
class Query:
    raw: str
    sides: tuple[tuple[str, ...], ...]  # name tokens per fighter; two sides for "A vs B"

    @property
    def is_matchup(self) -> bool:
        return len(self.sides) == 2


def parse_query(raw: str) -> Query:
    raw = " ".join(raw.split())
    sides = tuple(
        side
        for side in (tuple(t for t in tokens(part) if t not in _NOISE) for part in _VS.split(raw, maxsplit=1))
        if side
    )
    return Query(raw, sides)


def token_hit(token: str, candidates: list[str]) -> bool:
    """True if ``token`` appears in ``candidates``, tolerating a typo in longer words."""
    for candidate in candidates:
        if candidate == token:
            return True
        if len(token) >= _MIN_FUZZY_LEN and len(candidate) >= _MIN_FUZZY_LEN:
            if difflib.SequenceMatcher(None, candidate, token).ratio() >= _FUZZY_CUTOFF:
                return True
    return False


def _side_score(side: tuple[str, ...], title_tokens: list[str]) -> float:
    """0 if the surname is missing, else 0.7..1 depending on how much of the name matched."""
    if not token_hit(side[-1], title_tokens):
        return 0.0
    first_names = side[:-1]
    if not first_names:
        return 1.0
    return 0.7 + 0.3 * sum(token_hit(t, title_tokens) for t in first_names) / len(first_names)


def relevance(query: Query, title: str) -> tuple[str, float]:
    """Return (match, score). match is "full", "partial" or "none".

    For "A vs B" queries, "full" means both fighters appear in the title and "partial" only one.
    For free-text queries, "full" means every keyword appears.
    """
    title_tokens = tokens(title)
    if query.is_matchup:
        scores = [_side_score(side, title_tokens) for side in query.sides]
        hits = sum(1 for s in scores if s > 0)
        match = "full" if hits == 2 else "partial" if hits == 1 else "none"
        return match, sum(scores) / 2
    keywords = [t for side in query.sides for t in side]
    if not keywords:
        return "none", 0.0
    fraction = sum(token_hit(t, title_tokens) for t in keywords) / len(keywords)
    match = "full" if fraction == 1 else "partial" if fraction > 0 else "none"
    return match, fraction


def query_variants(query: Query) -> list[str]:
    """Search strings to send to each source."""
    if query.is_matchup:
        a, b = (" ".join(side) for side in query.sides)
        return [f"{a} vs {b}", f"{a} {b} full fight", f"{a} {b} highlights"]
    text = " ".join(query.sides[0]) if query.sides else query.raw
    return [f"{text} boxing", f"{text} boxing full fight"]
