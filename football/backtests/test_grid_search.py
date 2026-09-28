import unittest
from grid_search import *
from production_ratings import solve

class GridTests(unittest.TestCase):
    def test_design_and_refinement(self):
        cs=coarse();self.assertEqual(len(cs),25)
        self.assertEqual(len({tuple(c[k] for k in BASE) for c in cs}),25)
        for c in cs:
            rs=refine(c,cs)
            self.assertEqual(len(rs),10)
            self.assertEqual(len({tuple(r[k] for k in BASE) for r in cs+rs}),35)

    def test_baseline_prior_schedule(self):
        for w in range(4,17):self.assertEqual(weight(BASE,f'regular-{w:02}'),prior_weight(f'regular-{w:02}'))

    def test_batch_matches_production_and_independent_columns(self):
        games=load_games(2024)[:100]
        names={g[s+'Team'] for g in games for s in ('Home','Away')}
        priors={n:float(i%40-20) for i,n in enumerate(sorted(names))}
        cs=[dict(id='base',**BASE),dict(id='changed',**{**BASE,'bonus':6,'cap':42,'multiplier':1.5})]
        batch=fit_batch(games,{c['id']:priors for c in cs},cs,.75)
        expected=solve(games,priors,prior_weight=.75,margin_model='halftime1.25')
        self.assertLess(max(abs(expected[n]-batch['base'][n]) for n in names),1e-8)
        for c in cs:
            independent=fit_batch(games,{c['id']:priors},[c],.75)[c['id']]
            self.assertLess(max(abs(independent[n]-batch[c['id']][n]) for n in names),1e-8)

    def test_targets_and_fixed_guardrails(self):
        g={'HomePoints':42,'AwayPoints':7,'HomeLineScores':'14,21,0,7','AwayLineScores':'0,0,7,0'}
        self.assertEqual(targets([g],BASE)[0],46.5)
        self.assertEqual(targets([g],{**BASE,'multiplier':0,'cap':21,'bonus':0})[0],21)
        self.assertEqual(targets([g],{**BASE,'multiplier':2})[0],58.75)
        g['AwayPoints']=40;g['AwayLineScores']='0,0,20,20'
        self.assertEqual(targets([g],BASE)[0],4.75)

if __name__=='__main__':unittest.main()
