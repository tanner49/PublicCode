import math
import unittest

from ratings import build_snapshot, encode_margin, select_games, solve


def game(home="A", away="B", hp="50", ap="0", week="1", completed="true", **extra):
    return dict(Id="1", Season="2026", Week=week, SeasonType="regular", Completed=completed,
                HomeTeam=home, AwayTeam=away, HomePoints=hp, AwayPoints=ap,
                StartDate="2026-09-01T00:00:00Z", HomeClassification="fbs", AwayClassification="fbs", **extra)


class RatingsTests(unittest.TestCase):
    def test_one_game_prior_matches_original_pseudo_game_formula(self):
        games = select_games([game(hp="0", ap="0")], 2026, 3)
        # Each team has one real game: real row weight sqrt(1/2),
        # prior row weight 1. Targets are +/- (10 + winner bonus).
        ratings = solve(games, {"A": 10, "B": -10})
        self.assertAlmostEqual(ratings["A"], 12.75 / 2)
        self.assertAlmostEqual(ratings["B"], -12.75 / 2)
        weak = solve(games, {"A": 10, "B": -10}, prior_weight=0.00005)
        self.assertGreater(ratings["A"], weak["A"])

    def test_margin_is_symmetric_and_caps_blowouts(self):
        for margin in [0, 1, 27, 28, 29, 50, 100]:
            self.assertEqual(encode_margin(margin), -encode_margin(-margin))
        self.assertEqual(encode_margin(28), 30.75)
        self.assertEqual(encode_margin(100), 30.75)
        self.assertEqual(encode_margin(0), 0)

    def test_switching_venue_does_not_change_ratings(self):
        first = solve(select_games([game()], 2026, 3), {})
        second = solve(select_games([game(home="B", away="A", hp="0", ap="50")], 2026, 3), {})
        for team in first:
            self.assertAlmostEqual(first[team], second[team])
        self.assertAlmostEqual(first["A"] - first["B"], 30.75)
        self.assertAlmostEqual(sum(first.values()), 0)

    def test_cutoff_and_missing_scores(self):
        rows = [game(), dict(game(week="4"), Id="2"), dict(game(completed="false"), Id="3"), dict(game(hp=""), Id="4"), dict(game(), Id="5", Season="2025"), dict(game(), Id="6", SeasonType="postseason")]
        self.assertEqual([g["Id"] for g in select_games(rows, 2026, 3)], ["1"])

    def test_bad_scores_and_duplicates_rejected(self):
        for bad in ["NaN", "inf", "-1", "1.5", "n/a"]:
            with self.assertRaises(ValueError):
                select_games([game(hp=bad)], 2026, 3)
        with self.assertRaises(ValueError):
            select_games([game(), game()], 2026, 3)

    def test_snapshot_records_and_unrated_fixture(self):
        rows = [game(), dict(game(home="C", week="4", completed="false", hp="", ap=""), Id="2"), dict(game(hp=""), Id="3")]
        snapshot = build_snapshot(rows, 2026, 4, {}, "test")
        self.assertEqual(snapshot["gameCount"], 1)
        self.assertEqual(snapshot["excludedMissingScores"], ["3"])
        a, b = snapshot["teams"]
        self.assertEqual((a["team"], a["wins"], a["divisionRank"]), ("A", 1, 1))
        self.assertEqual(b["losses"], 1)
        self.assertIsNone(snapshot["fixtures"][0]["homeEdge"])
        self.assertTrue(all(math.isfinite(t["rating"]) for t in snapshot["teams"]))


if __name__ == "__main__":
    unittest.main()
