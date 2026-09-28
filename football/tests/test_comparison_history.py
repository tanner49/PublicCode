import copy
import json
import unittest

from comparison_history import comparison_history
from ratings import ROOT, build_snapshot, read_csv


class ComparisonHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=json.loads((ROOT/'data/generated/2026/week-04.json').read_text(encoding='utf-8'))
        cls.current=json.loads((ROOT/'data/generated/2026/week-05.json').read_text(encoding='utf-8'))

    def test_matches_historical_inputs_with_new_rule_and_preserves_publication(self):
        before=copy.deepcopy(self.old)
        result=comparison_history(self.current,[self.old])['history'][0]
        priors={r['Team']:float(r['MasseyRating']) for r in read_csv(ROOT/'data/generated/priors-2025.csv')}
        expected=build_snapshot(read_csv(ROOT/'data/raw/2026/week-04.csv'),2026,4,priors,
                                self.old['sourceSha256'],prior_weight=1,margin_model='halftime1.25')
        self.assertEqual(self.old,before)
        self.assertEqual(result['model']['priorWeight'],1)
        self.assertEqual({t['team']:t['rating'] for t in result['teams']},
                         {t['team']:t['rating'] for t in expected['teams']})
        self.assertEqual(next(t['divisionRank'] for t in result['teams'] if t['team']=='Georgia'),7)
        self.assertEqual(next(t['divisionRank'] for t in self.old['teams'] if t['team']=='Georgia'),13)

    def test_current_game_results_cannot_change_historical_comparison(self):
        altered=copy.deepcopy(self.current)
        for t in altered['teams']:
            t['rating']=999
            for g in t['games']:g['scored']=99
        self.assertEqual(comparison_history(altered,[self.old]),comparison_history(self.current,[self.old]))

    def test_mismatched_historical_source_rejected(self):
        altered=copy.deepcopy(self.old);altered['sourceSha256']='bad'
        with self.assertRaises(ValueError):comparison_history(self.current,[altered])


if __name__=='__main__':unittest.main()
