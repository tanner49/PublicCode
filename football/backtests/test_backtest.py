import copy
import json
import unittest
from backtest import *

class BacktestTests(unittest.TestCase):
    def test_grading_home_away_push_and_pass(self):
        # Home -7: home pick if model predicts >7; road pick if <7.
        self.assertEqual(grade(10,7,14),'W')
        self.assertEqual(grade(10,7,3),'L')
        self.assertEqual(grade(3,7,3),'W')
        self.assertEqual(grade(3,7,14),'L')
        self.assertEqual(grade(10,7,7),'P')
        self.assertEqual(grade(7,7,14),'PASS')
        self.assertEqual(grade(-3,-7,-4),'W')

    def test_prior_schedule(self):
        self.assertEqual([prior_weight(f'regular-{w:02}') for w in range(4,10)], [1,.75,.5,.25,0,0])
        self.assertEqual(prior_weight('postseason-2024-01-01'),0)

    def test_future_scores_do_not_change_training_or_ratings(self):
        games=load_games(2024)
        cutoff,train=training_window(games,'regular-04')
        altered=copy.deepcopy(games)
        for g in altered:
            if stamp(g['StartDate'])>=cutoff:
                g['HomePoints']=99;g['AwayPoints']=0
                g['HomeLineScores']='50,49,0,0';g['AwayLineScores']='0,0,0,0'
        cutoff2,train2=training_window(altered,'regular-04')
        self.assertEqual(cutoff,cutoff2)
        self.assertEqual(train,train2)
        self.assertEqual(solve(train,{},prior_weight=1,margin_model='halftime1.25'),
                         solve(train2,{},prior_weight=1,margin_model='halftime1.25'))

    def test_all_saved_windows_and_no_bets_before_four(self):
        audits=json.loads((OUT/'weekly-audit.json').read_text())
        all_games={y:{g['Id']:g for g in load_games(y)} for y in (2023,2024,2025)}
        for audit in audits:
            games=all_games[audit['season']]
            cutoff=stamp(audit['cutoff'])
            self.assertFalse(set(audit['trainIds'])&set(audit['fixtures']))
            for ident in audit['trainIds']:
                self.assertLess(stamp(games[ident]['StartDate'])+timedelta(hours=12),cutoff)
            for ident in audit['fixtures']:
                self.assertGreaterEqual(stamp(games[ident]['StartDate']),cutoff)
                if games[ident]['SeasonType']=='regular':
                    self.assertGreaterEqual(int(games[ident]['Week']),4)

    def test_profit_accounting(self):
        s=summary([{'halftime1.25Result':x} for x in ['W','L','W','P','PASS']])
        self.assertEqual(s['profit'],90)
        self.assertEqual(s['risked'],440)
        self.assertEqual(s['winRate'],2/3)

    def test_half_rule_and_missing_quarters(self):
        g={'HomePoints':42,'AwayPoints':7,'HomeLineScores':'14,21,0,7','AwayLineScores':'0,0,7,0'}
        self.assertEqual(game_target(g,'halftime1.25'),46.5)
        g['HomeLineScores']=''
        self.assertEqual(game_target(g,'halftime1.25'),30.75)

if __name__=='__main__':
    unittest.main()
