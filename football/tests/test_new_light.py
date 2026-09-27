import unittest

from ratings import build_snapshot, select_games, solve
from new_light import analyze


def game(id, home, away, hp, ap, week):
    return dict(Id=id, HomeTeam=home, AwayTeam=away, HomePoints=str(hp), AwayPoints=str(ap),
                Season='2026', SeasonType='regular', Completed='true', Week=str(week),
                StartDate=f'2026-09-{week:02}T00:00:00Z', HomeClassification='fbs', AwayClassification='fbs')


class NewLightTests(unittest.TestCase):
    def setUp(self):
        self.old = [game('1', 'A', 'B', 24, 21, 1), game('2', 'C', 'D', 21, 17, 1),
                    game('3', 'B', 'C', 21, 20, 2)]
        self.priors = {'A': 10, 'B': 8, 'C': 5, 'D': 2}
        self.previous = build_snapshot(self.old, 2026, 4, self.priors, 'old')

    def current(self, new):
        return build_snapshot(self.old + new, 2026, 5, self.priors, 'new', prior_weight=.75)

    def test_prior_only_is_not_a_new_light_change(self):
        current = self.current([])
        self.assertEqual(current['model']['priorWeight'], .75)
        expected = solve(select_games(self.old, 2026, 4), self.priors, prior_weight=.75)
        self.assertAlmostEqual(current['teams'][0]['rating'], max(expected.values()), places=5)
        for row in analyze(self.previous, current, self.priors)['teams']:
            self.assertAlmostEqual(row['change'], 0)
            self.assertAlmostEqual(row['ownGameEffect'], 0)

    def test_own_game_excluded_but_old_opponents_revalued(self):
        result = analyze(self.previous, self.current([game('4', 'B', 'D', 50, 0, 4)]), self.priors)
        rows = {r['team']: r for r in result['teams']}
        self.assertAlmostEqual(rows['B']['change'], 0)
        self.assertAlmostEqual(rows['D']['change'], 0)
        self.assertGreater(rows['A']['change'], 0)
        self.assertEqual(rows['B']['excludedOwnGameIds'], ['4'])
        for row in result['teams']:
            total = row['priorChange'] + row['historicalCorrectionEffect'] + row['change'] + row['ownGameEffect']
            self.assertAlmostEqual(total, row['currentPublishedRating'] - row['previousPublishedRating'], places=5)
        self.assertEqual([abs(r['change']) for r in result['teams']], sorted([abs(r['change']) for r in result['teams']], reverse=True))

    def test_historical_corrections_do_not_count_as_new_results(self):
        corrected = [dict(g) for g in self.old]
        corrected[0]['HomePoints'] = '40'
        current = build_snapshot(corrected, 2026, 5, self.priors, 'corrected', prior_weight=.75)
        result = analyze(self.previous, current, self.priors)
        self.assertEqual(result['correctedHistoricalGameIds'], ['1'])
        for row in result['teams']:
            self.assertAlmostEqual(row['change'], 0)
        self.assertTrue(any(abs(r['historicalCorrectionEffect']) > .01 for r in result['teams']))

    def test_margin_rule_change_is_separate_from_elsewhere_results(self):
        rows = [game('1', 'A', 'B', 35, 0, 1)]
        rows[0].update(HomeLineScores='14,14,7,0', AwayLineScores='0,0,0,0')
        previous = build_snapshot(rows, 2026, 4, self.priors, 'old', prior_weight=.75)
        current = build_snapshot(rows, 2026, 5, self.priors, 'new', prior_weight=.75, margin_model='halftime1.25')
        result = analyze(previous, current, self.priors)
        for row in result['teams']:
            self.assertAlmostEqual(row['change'], 0)
            self.assertAlmostEqual(row['historicalCorrectionEffect'], 0)
            self.assertAlmostEqual(row['modelChangeEffect'], row['currentPublishedRating'] - row['previousPublishedRating'], places=5)
        self.assertTrue(any(abs(r['modelChangeEffect']) > .1 for r in result['teams']))


if __name__ == '__main__':
    unittest.main()
