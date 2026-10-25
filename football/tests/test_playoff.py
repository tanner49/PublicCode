import unittest
from playoff import select_field, build_playoff, project_champions, POWER

def team(name,rating,conference):
    return dict(team=name,rating=rating,conference=conference,classification='fbs')

class PlayoffTests(unittest.TestCase):
    def setUp(self):
        self.teams=[team(f'T{i}',100-i,'SEC') for i in range(1,21)]
        self.teams += [team('ACC winner',55,'ACC'),team('Big Ten winner',54,'Big Ten'),team('Big 12 winner',53,'Big 12'),team('G6 leader',52,'Pac-12')]
        self.champions={c:dict(team=n) for c,n in [('ACC','ACC winner'),('Big Ten','Big Ten winner'),('Big 12','Big 12 winner'),('SEC','T3')]}
        self.snapshot=dict(season=2026,week=9,throughWeek=8,teams=self.teams)
    def test_automatic_bids_displace_top12_but_byes_follow_rating(self):
        field=select_field(self.snapshot,self.champions);names={t['team'] for t in field}
        self.assertEqual(len(names),12)
        self.assertTrue({'ACC winner','Big Ten winner','Big 12 winner','G6 leader'}<=names)
        self.assertNotIn('T12',names)
        self.assertEqual([t['team'] for t in field[:4]],['T1','T2','T3','T4'])
    def test_group_bid_does_not_require_a_conference_title(self):
        self.snapshot['teams'].append(team('American contender',90.5,'American Athletic'))
        qualifier=next(t for t in select_field(self.snapshot,self.champions) if t['bid']=='Group of Six bid')
        self.assertEqual(qualifier['team'],'American contender')
        self.assertNotIn(qualifier['team'],[v['team'] for v in self.champions.values()])
    def test_notre_dame_top12_guarantee(self):
        self.snapshot['teams']=[t for t in self.teams if t['team']!='T12']+[team('Notre Dame',88,'FBS Independents')]
        field=select_field(self.snapshot,self.champions);nd=next(t for t in field if t['team']=='Notre Dame')
        self.assertEqual(nd['modelRank'],12)
        self.assertEqual(nd['bid'],'Notre Dame guarantee')
        self.assertEqual(len(field),12)
        self.assertNotIn('T8',{t['team'] for t in field})
    def test_historical_projection_ignores_future_completed_scores(self):
        teams=[];games=[]
        for i,c in enumerate(POWER):
            h=f'{c} A';a=f'{c} B';teams += [team(h,10,c),team(a,0,c)]
            games.append(dict(Id=str(i),Season='2026',SeasonType='regular',ConferenceGame='true',HomeTeam=h,AwayTeam=a,Week='10',Completed='true',HomePoints='0',AwayPoints='99',NeutralSite='false'))
        snapshot=dict(season=2026,week=9,throughWeek=8,teams=teams)
        champs,results=project_champions(snapshot,games)
        self.assertTrue(all(r['projected'] and r['homeMargin']==13 for r in results))
        self.assertTrue(all(champs[c]['team']==f'{c} A' for c in POWER))
        snapshot['week']=11
        _,results=project_champions(snapshot,games)
        self.assertTrue(all(not r['projected'] and r['homeMargin']==-99 for r in results))
    def test_unknown_season_requires_review(self):
        self.snapshot['season']=2027
        with self.assertRaises(ValueError):build_playoff(self.snapshot,[])

if __name__=='__main__':unittest.main()
