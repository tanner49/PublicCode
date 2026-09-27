import unittest

from analysis.halftime_2025 import target


def game(hp, ap, h, a):
    return dict(HomePoints=hp, AwayPoints=ap, HomeLineScores=h, AwayLineScores=a)


class HalftimeTests(unittest.TestCase):
    def test_early_dominance_distinguishes_identical_final_margins(self):
        early = game(35, 0, '14,14,7,0', '0,0,0,0')
        late = game(35, 0, '7,7,7,14', '0,0,0,0')
        self.assertEqual(target(early, 'half1.25'), 37.75)
        self.assertEqual(target(late, 'half1.25'), 30.75)

    def test_collapse_does_not_keep_blowout_credit(self):
        self.assertEqual(target(game(35, 34, '14,14,7,0', '0,0,14,20'), 'half1.25'), 3.75)
        self.assertEqual(target(game(28, 35, '14,14,0,0', '0,0,14,21'), 'half1.25'), -9.75)

    def test_missing_quarters_cap_and_symmetry(self):
        self.assertEqual(target(game(70, 0, '28,28,7,7', '0,0,0,0'), 'half1.25'), 58.75)
        self.assertEqual(target(game(35, 0, '', '0,0,0,0'), 'half1.25'), 30.75)
        self.assertEqual(target(game(0, 35, '0,0,0,0', '14,14,7,0'), 'half1.25'), -37.75)


if __name__ == '__main__':
    unittest.main()
