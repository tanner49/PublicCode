import unittest
from game_state_backtest import *

def game(h,a):return dict(HomePoints=sum(h),AwayPoints=sum(a),HomeLineScores=','.join(map(str,h)),AwayLineScores=','.join(map(str,a)))

class StateTests(unittest.TestCase):
    def test_weight_uses_lead_time_and_is_symmetric(self):
        self.assertEqual(quarter_weight(100,0),1)
        self.assertEqual(quarter_weight(14,3),1)
        self.assertEqual(quarter_weight(28,3),.5)
        self.assertEqual(quarter_weight(-28,3),.5)
        self.assertLess(quarter_weight(35,3),quarter_weight(35,1))

    def test_overtime_only_gets_winner_bonus(self):
        g=game([7,7,7,7,7,7],[7,7,7,7,0,0])
        for _,rule in RULES[1:]:self.assertEqual(target(g,rule),2.75)

    def test_slow_start_not_erased(self):
        g=game([0,0,21,14],[14,0,0,0])
        self.assertEqual(target(g,'state_soft_ot'),23.75)

    def test_late_pile_on_and_giveback(self):
        pile=game([14,21,0,28],[0,0,0,0])
        give=game([14,21,0,0],[0,0,0,18])
        self.assertLess(target(pile,'state_soft_ot'),target(pile,'soft_ot'))
        self.assertGreater(target(give,'state_soft_ot'),target(give,'soft_ot'))

    def test_recovery_restores_next_quarter_weight(self):
        # Down 35 at half, score 28 in Q3, then win Q4 14-0.
        g=game([0,0,28,14],[14,21,0,0])
        self.assertEqual(quarter_weight(-7,3),1)
        self.assertAlmostEqual(target(g,'state_soft_ot'),-7+2.75)

    def test_swap_negates_every_target(self):
        for h,a in [([0,0,28,14],[14,21,0,0]),([21,21,0,0],[0,0,14,7]),([7,7,0,0,7],[7,7,0,0,0])]:
            for _,rule in RULES:self.assertAlmostEqual(target(game(h,a),rule),-target(game(a,h),rule))

    def test_invalid_quarters_fallback(self):
        g=game([14,21,7,0],[0,0,0,0]);g['HomeLineScores']='14,21'
        for _,rule in RULES:self.assertEqual(target(g,rule),30.75)

if __name__=='__main__':unittest.main()
