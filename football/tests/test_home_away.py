import unittest
from analysis.home_away_2026 import calculate

class HomeAwayTests(unittest.TestCase):
    def snapshot(self):
        games=[dict(id=str(i),venue=venue,opponent='B',scored=score,allowed=0) for i,(venue,score) in enumerate([('H',20)]*3+[('A',10)]*3+[('N',100)])]
        return dict(model={'homeAdvantage':3},teams=[dict(team='A',rating=10,classification='fbs',conference='Test',games=games),dict(team='B',rating=0,classification='fbs',conference='Test',games=[]),dict(team='C',rating=0,classification='fcs',conference='Test',games=[])])
    def test_current_rating_residuals_include_venue_adjustment_and_exclude_neutral(self):
        r=calculate(self.snapshot())[0]
        self.assertEqual(r['homeGames'],3);self.assertEqual(r['awayGames'],3)
        self.assertEqual(r['homeMean'],7);self.assertEqual(r['awayMean'],3);self.assertEqual(r['homeMinusAway'],4)
    def test_opponent_scope_and_sample_minimum(self):
        s=self.snapshot();s['teams'][0]['games'].append(dict(id='fcs',venue='H',opponent='C',scored=60,allowed=0))
        self.assertEqual(calculate(s)[0]['homeMean'],7)
        self.assertEqual(calculate(s,False)[0]['homeMean'],17)
        s['teams'][0]['games']=[g for g in s['teams'][0]['games'] if g['id']!='3']
        self.assertEqual(calculate(s),[])
