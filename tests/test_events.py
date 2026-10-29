import unittest

from fightnight.events import load_events, match_event, suggestions
from fightnight.names import parse_query


class EventTests(unittest.TestCase):
    events = load_events()

    def test_exactly_one_suggestion_for_kakande_muxanga(self):
        self.assertEqual(
            [s["query"] for s in suggestions(self.events)],
            ["Muzamiru Kakande vs Tiago Muxanga"],
        )

    def test_suggestion_matches_its_own_event(self):
        query = parse_query(suggestions(self.events)[0]["query"])
        self.assertEqual(match_event(query, self.events)["id"], "kakande-muxanga-2026-10-25")

    def test_matches_loose_spelling_and_order(self):
        self.assertIsNotNone(match_event(parse_query("muxanga v kakandi"), self.events))

    def test_needs_both_fighters(self):
        self.assertIsNone(match_event(parse_query("Muxanga"), self.events))
        self.assertIsNone(match_event(parse_query("Fury vs Usyk"), self.events))

    def test_no_free_broadcast_is_claimed(self):
        event = self.events[0]
        self.assertTrue(all(b["cost"] != "Free" for b in event["broadcast"]))


if __name__ == "__main__":
    unittest.main()
