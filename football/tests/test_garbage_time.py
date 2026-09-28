import unittest

from experiments.garbage_time_2025 import adjusted_game, adjusted_margin, quarter_margin


def game(home, away):
    return {"HomePoints": sum(home), "AwayPoints": sum(away),
            "HomeLineScores": ",".join(map(str, home)), "AwayLineScores": ",".join(map(str, away))}


class GarbageTimeTests(unittest.TestCase):
    def test_qualifying_win_and_venue_symmetry(self):
        self.assertEqual(adjusted_margin(game([14, 14, 7, 0], [0, 7, 0, 14])), 28)
        self.assertEqual(adjusted_margin(game([0, 7, 0, 14], [14, 14, 7, 0])), -28)

    def test_ten_point_boundary(self):
        self.assertEqual(adjusted_margin(game([14, 14, 7, 0], [0, 7, 0, 18])), 28)
        self.assertEqual(adjusted_margin(game([14, 14, 7, 0], [0, 7, 0, 19])), 9)

    def test_lead_threshold_and_lost_lead(self):
        self.assertEqual(adjusted_margin(game([14, 13, 7, 0], [0, 7, 0, 14])), 13)
        self.assertEqual(adjusted_margin(game([14, 14, 7, 0], [0, 7, 0, 42])), -14)

    def test_missing_or_inconsistent_quarters_fall_back(self):
        original = game([14, 14, 7, 0], [0, 7, 0, 14])
        for invalid in ["", "14,14", "14,14,x,0", "14,14,7,1"]:
            changed = dict(original, HomeLineScores=invalid)
            self.assertIsNone(quarter_margin(changed))
            self.assertEqual(adjusted_margin(changed), 14)

    def test_training_transformation_does_not_mutate_outcome(self):
        original = game([14, 14, 7, 0], [0, 7, 0, 14])
        transformed = adjusted_game(original)
        self.assertEqual(original["HomePoints"] - original["AwayPoints"], 14)
        self.assertEqual(transformed["HomePoints"] - transformed["AwayPoints"], 28)


if __name__ == "__main__":
    unittest.main()
