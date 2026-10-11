import unittest
from ratings import solve, build_snapshot
from profile_metrics import reconstruct_games
class HomeAdjustmentTests(unittest.TestCase):
 def test_one_point_home_road_neutral_and_cap(self):
  for hp,ap,neutral,expected in [(21,20,False,.75),(20,21,False,-6.75),(21,20,True,3.75),(60,0,False,27.75)]:
   fit=solve([dict(HomeTeam='A',AwayTeam='B',HomePoints=hp,AwayPoints=ap,NeutralSite=neutral)],{},prior_weight=0,home_advantage=3)
   self.assertAlmostEqual(fit['A']-fit['B'],expected)
 def test_reconstruct_preserves_venue(self):
  rows=[]
  for i,(a,b,hp,ap,n) in enumerate([('A','B',10,30,False),('B','C',31,7,True),('C','A',24,21,False)]):
   rows.append(dict(Id=str(i),HomeTeam=a,AwayTeam=b,HomePoints=str(hp),AwayPoints=str(ap),NeutralSite=str(n),Season='2026',Week='1',SeasonType='regular',Completed='true',StartDate='2026-09-01T00:00:00Z'))
  snap=build_snapshot(rows,2026,4,{},'test',prior_weight=0,home_advantage=3)
  rebuilt=solve(reconstruct_games(snap),{},prior_weight=0,home_advantage=3)
  for t in snap['teams']:self.assertAlmostEqual(t['rating'],rebuilt[t['team']],places=5)
