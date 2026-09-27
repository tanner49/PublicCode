"""Compare cap28 and halftime1.25 on Week 4 with identical 0.75 prior/+3 home."""
import csv
import hashlib
import json
import math
from pathlib import Path

import halftime_2025 as experiment
from ratings import read_csv, select_games, solve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/results/halftime-2026-week04'


def grade(prediction, market, actual):
    edge = prediction-market
    return 'PASS' if edge == 0 else 'P' if actual == market else 'W' if edge*(actual-market)>0 else 'L'


def main():
    train_path = ROOT / 'data/raw/2026/week-04.csv'
    prior_path = ROOT / 'data/generated/priors-2025.csv'
    lines_path = ROOT / 'analysis/results/2026-week04-ats/game-by-game.csv'
    snapshot_path = ROOT / 'data/generated/2026/week-04.json'
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
    assert hashlib.sha256(train_path.read_bytes()).hexdigest() == snapshot['sourceSha256']
    assert hashlib.sha256(prior_path.read_bytes()).hexdigest() == snapshot['priorSha256']
    games = select_games(read_csv(train_path), 2026, 3)
    fixtures = {g['id']: g for g in snapshot['fixtures']}
    lines = read_csv(lines_path)
    cutoff = min(g['date'] for g in snapshot['fixtures'])
    assert all(g['StartDate'] < cutoff for g in games)
    priors = {r['Team']:float(r['MasseyRating']) for r in read_csv(prior_path)}
    experiment.VARIANTS = ['cap28', 'half1.25']
    fits = experiment.fit_all(games, priors, .75)
    expected = solve(games, priors, prior_weight=.75)
    assert max(abs(expected[t]-fits['cap28'][t]) for t in expected)<1e-8
    rows=[]
    for line in lines:
        game=fixtures[line['id']]
        actual=float(line['actualHomeMargin']);market=float(line['marketHomeMargin'])
        row={k:line[k] for k in ['id','away','home','basis','bothFBS','homeScore','awayScore']}
        row.update(actualHomeMargin=actual,marketHomeMargin=market)
        for label,rating in fits.items():
            raw=rating[game['home']]-rating[game['away']] + (0 if game['neutral'] else 3)
            # Match the stored forecast's two decimals then displayed half-point rule.
            stored=round(raw,2)
            rounded=math.copysign(math.floor(abs(stored)*2+.5)/2,stored)
            row[label+'Raw']=raw;row[label+'Line']=rounded
            row[label+'Result']=grade(rounded,market,actual)
            row[label+'RawResult']=grade(raw,market,actual)
            row[label+'Pick']='PASS' if rounded==market else game['home'] if rounded>market else game['away']
        rows.append(row)
    groups={'confirmedClose':[r for r in rows if r['basis']=='Close'],
            'FBSvsFBS':[r for r in rows if r['basis']=='Close' and r['bothFBS']=='True'],
            'FBSvsFCS':[r for r in rows if r['basis']=='Close' and r['bothFBS']=='False'],
            'allSupplied':rows}
    summary={}
    for name,rs in groups.items():
        summary[name]={}
        for model in fits:
            summary[name][model]={'games':len(rs),
                **{outcome:sum(r[model+'Result']==outcome for r in rs) for outcome in ['W','L','P','PASS']},
                'rawResults':{outcome:sum(r[model+'RawResult']==outcome for r in rs) for outcome in ['W','L','P','PASS']},
                'MAE':sum(abs(r[model+'Raw']-r['actualHomeMargin']) for r in rs)/len(rs),
                'underdogPicks':sum(r[model+'Pick']!='PASS' and r[model+'Pick']!=(r['home'] if r['marketHomeMargin']>0 else r['away']) for r in rs)}
    summary['training']={'games':len(games),'validQuarters':sum(experiment.halftime(g) is not None for g in games),
                         'changedTargets':sum(experiment.target(g,'cap28')!=experiment.target(g,'half1.25') for g in games),
                         'priorWeight':.75,'homeAdvantage':3,
                         'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [train_path,prior_path,lines_path,snapshot_path]}}
    OUT.mkdir(parents=True,exist_ok=True)
    for name,rs in [('game-by-game',rows),('ratings',[{'team':n,**{m:fits[m][n] for m in fits}} for n in expected])]:
        with (OUT/f'{name}.csv').open('w',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rs[0]));writer.writeheader();writer.writerows(rs)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    for r in rows:
        if r['basis']=='Close' and r['cap28Pick']!=r['half1.25Pick']:
            print('CHANGED',r['away'],'at',r['home'],r['cap28Pick'],r['cap28Result'],'->',r['half1.25Pick'],r['half1.25Result'])


if __name__=='__main__':
    main()
