import unittest

from fightnight.names import parse_query, query_variants, relevance, tokens


class ParseQueryTests(unittest.TestCase):
    def test_matchup_separators(self):
        for sep in ("vs", "VS", "vs.", "v", "versus"):
            q = parse_query(f"Muzamiru Kakande {sep} Tiago Muxanga")
            self.assertEqual(q.sides, (("muzamiru", "kakande"), ("tiago", "muxanga")), sep)
            self.assertTrue(q.is_matchup)

    def test_free_text_is_single_side(self):
        q = parse_query("  Kakande   boxing full fight ")
        self.assertEqual(q.sides, (("kakande",),))
        self.assertFalse(q.is_matchup)

    def test_only_noise_has_no_sides(self):
        self.assertEqual(parse_query("boxing live stream").sides, ())

    def test_accents_are_stripped(self):
        self.assertEqual(tokens("Saúl Álvarez"), ["saul", "alvarez"])


class RelevanceTests(unittest.TestCase):
    q = parse_query("Muzamiru Kakande vs Tiago Muxanga")

    def test_both_fighters(self):
        match, score = relevance(self.q, "Kakande vs Muxanga | FULL FIGHT")
        self.assertEqual(match, "full")
        self.assertAlmostEqual(score, 0.7)  # surnames only
        self.assertAlmostEqual(relevance(self.q, "Muzamiru Kakande vs Tiago Muxanga")[1], 1.0)

    def test_full_names_score_higher_than_surnames(self):
        _, surnames = relevance(self.q, "Kakande vs Muxanga")
        _, full_names = relevance(self.q, "Muzamiru Kakande vs Tiago Muxanga")
        self.assertGreater(full_names, surnames)

    def test_one_fighter_is_partial(self):
        self.assertEqual(relevance(self.q, "Tiago Muxanga wins IBO title")[0], "partial")

    def test_unrelated_is_none(self):
        self.assertEqual(relevance(self.q, "Fury vs Usyk 2 full fight")[0], "none")

    def test_typo_in_title_still_matches(self):
        self.assertEqual(relevance(self.q, "Kakandi vs Muxangah")[0], "full")

    def test_short_words_need_exact_match(self):
        q = parse_query("Wu vs Li")
        self.assertEqual(relevance(q, "Wi vs La")[0], "none")

    def test_free_text(self):
        q = parse_query("kakande")
        self.assertEqual(relevance(q, "Kakande knockout")[0], "full")
        self.assertEqual(relevance(parse_query("kakande muxanga"), "Kakande knockout")[0], "partial")


class VariantTests(unittest.TestCase):
    def test_matchup_variants(self):
        variants = query_variants(parse_query("Muzamiru Kakande vs Tiago Muxanga"))
        self.assertEqual(variants[0], "muzamiru kakande vs tiago muxanga")
        self.assertEqual(len(variants), 3)

    def test_free_text_adds_boxing(self):
        self.assertTrue(all("boxing" in v for v in query_variants(parse_query("kakande"))))


if __name__ == "__main__":
    unittest.main()
