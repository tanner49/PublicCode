"""Controlled 2026 retrospective training-home-advantage comparison."""
import sys,json,math,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import ratings
OUT=ROOT/'analysis/results/home-adjustment-2026';OUT.mkdir(exist_ok=True,parents=True)
priors={r['Team']:float(r['MasseyRating']) for r in ratings.read_csv(ROOT/'data/generated/priors-2025.csv')}
original=ratings.game_target
rows=[];audit=[]
def grade(p,v,a):return 'PASS' if p==v else 'P' if a==v else 'W' if (p-v)*(a-v)>0 else 'L'
for week,weight in [(4,.75),(5,.75),(6,.5)]:
 source=ROOT/f'data/raw/2026/week-{week:02}.csv';snapshot=json.loads((ROOT/f'data/generated/2026/week-{week:02}.json').read_text(encoding='utf8'));fixtures={r['id']:r for r in snapshot['fixtures']};games=ratings.select_games(ratings.read_csv(source),2026,week-1)
 assert hashlib.sha256(source.read_bytes()).hexdigest()==snapshot['sourceSha256']
 if week==4:
  lines=[dict(id=r['id'],actual=float(r['actualHomeMargin']),market=float(r['marketHomeMargin']),expected=float(r['half1.25Line'])) for r in ratings.read_csv(ROOT/'analysis/results/halftime-2026-week04/game-by-game.csv') if r['basis']=='Close']
 else:
  path=ROOT/('data/odds-snapshots/20261002T212356Z/final-week05-results.json' if week==5 else 'data/odds-snapshots/week06-20261010T193618Z/final-week06-results.json')
  lines=[dict(id=r['id'],actual=int(r['home_score'])-int(r['away_score']),market=-float(r['vegas_home_spread'] if week==5 else r['home_spread']),expected=r['prediction']) for r in json.loads(path.read_text(encoding='utf8'))['results']]
 cutoff=min(fixtures[r['id']]['date'] for r in lines);assert all(g['StartDate']<cutoff for g in games);assert not {r['id'] for r in lines}&{g['Id'] for g in games}
 fits={}
 for name,hfa in [('baseline',0),('adjusted',3)]:
  ratings.game_target=lambda g,margin_model='cap28',h=hfa:original(g,margin_model)-(0 if ratings.truth(g.get('NeutralSite')) else h)
  fits[name]=ratings.solve(games,priors,prior_weight=weight,margin_model='halftime1.25')
 ratings.game_target=original
 for line in lines:
  f=fixtures[line['id']];r=dict(week=week,id=line['id'],home=f['home'],away=f['away'],actual=line['actual'],market=line['market'])
  for name,fit in fits.items():
   raw=fit[f['home']]-fit[f['away']]+(0 if f['neutral'] else 3);stored=round(raw,2);pred=math.copysign(math.floor(abs(stored)*2+.5)/2,stored);r[name+'Raw']=raw;r[name+'Line']=pred;r[name+'ATS']=grade(pred,r['market'],r['actual'])
  assert r['baselineLine']==line['expected'],(week,line,r)
  rows.append(r)
 audit.append(dict(week=week,prior_weight=weight,training_games=len(games),cutoff=cutoff,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
summary={}
for week in [4,5,6,'all']:
 rs=[r for r in rows if week=='all' or r['week']==week];summary[str(week)]={}
 for name in fits:
  err=np.array([r[name+'Raw']-r['actual'] for r in rs]);summary[str(week)][name]=dict(Counter(r[name+'ATS'] for r in rs),MAE=float(abs(err).mean()),RMSE=float(np.sqrt((err**2).mean())),home_bias=float(err.mean()))
summary['changed_picks']=[r for r in rows if np.sign(r['baselineLine']-r['market'])!=np.sign(r['adjustedLine']-r['market'])]
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');(OUT/'games.json').write_text(json.dumps(rows,indent=2),encoding='utf8');(OUT/'audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k!='changed_picks'},indent=2));print('Changed picks',len(summary['changed_picks']))
