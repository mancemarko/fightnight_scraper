import unittest

from fightnight.classify import detect_kind, is_official, load_official_channels, parse_duration


def kind(title, live=False, upcoming=False, duration=None):
    return detect_kind(title, live=live, upcoming=upcoming, duration_seconds=duration)


class DurationTests(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_duration("1:02:03"), 3723)
        self.assertEqual(parse_duration("12:34"), 754)
        self.assertIsNone(parse_duration(""))
        self.assertIsNone(parse_duration("LIVE"))


class KindTests(unittest.TestCase):
    def test_live_and_upcoming_win(self):
        self.assertEqual(kind("Full fight highlights", live=True), "live")
        self.assertEqual(kind("Full fight", upcoming=True), "upcoming")

    def test_titles(self):
        self.assertEqual(kind("Kakande vs Muxanga FULL FIGHT"), "full")
        self.assertEqual(kind("Kakande vs Muxanga highlights"), "highlights")
        self.assertEqual(kind("Round 3 KO"), "highlights")
        self.assertEqual(kind("Kakande vs Muxanga weigh-in"), "extra")
        self.assertEqual(kind("Kakande vs Muxanga"), "other")

    def test_long_untitled_video_counts_as_full(self):
        self.assertEqual(kind("Kakande vs Muxanga", duration=40 * 60), "full")
        self.assertEqual(kind("Kakande vs Muxanga", duration=5 * 60), "other")

    def test_highlights_beat_long_duration(self):
        self.assertEqual(kind("Highlights show", duration=3600), "highlights")


class OfficialTests(unittest.TestCase):
    channels = load_official_channels()

    def test_requires_name_and_badge(self):
        self.assertTrue(is_official("DAZN Boxing", True, self.channels))
        self.assertTrue(is_official("dazn  boxing", True, self.channels))

    def test_lookalike_without_badge_is_not_official(self):
        self.assertFalse(is_official("DAZN Boxing", False, self.channels))

    def test_name_must_match_exactly(self):
        self.assertFalse(is_official("DAZN Boxing Full Fights HD", True, self.channels))
        self.assertFalse(is_official("Some Verified Channel", True, self.channels))


if __name__ == "__main__":
    unittest.main()
