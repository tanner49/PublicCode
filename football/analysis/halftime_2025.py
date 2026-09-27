"""Frozen-through-Week-10 holdout test of halftime-aware blowout targets.

Run from any directory. Does not change ratings.py or website snapshots.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ratings import BONUS, encode_margin, read_csv, select_games, solve, truth

OUT = ROOT / 'analysis/results/halftime-2025'
VARIANTS = ['cap28', 'half1.0', 'half1.25', 'half1.5', 'softcap25pct', 'uncapped']


def halftime(g):
    scores = []
    for side in ('Home', 'Away'):
        try:
            periods = [int(x.strip()) for x in g.get(side+'LineScores', '').split(',')]
        except (ValueError, TypeError):
            return None
        if len(periods) < 4 or min(periods) < 0 or sum(periods) != g[side+'Points']:
            return None
        scores.append(sum(periods[:2]))
    return scores[0] - scores[1]


def target(g, variant):
    final = g['HomePoints']-g['AwayPoints']
    if not final:
        return 0.
    credit = min(abs(final), 28)
    if variant.startswith('half'):
        half = halftime(g)
        # Only the eventual winner can get extra credit. Guard against collapses.
        if half is not None and half*final > 0 and abs(half) >= 21 and abs(final) >= 10:
            credit = max(credit, min(56, float(variant[4:])*abs(half)))
    elif variant == 'softcap25pct':
        credit = min(56, credit + .25*max(0, abs(final)-28))
    elif variant == 'uncapped':
        credit = abs(final)
    return math.copysign(credit + BONUS, final)


def fit_all(games, priors, prior_weight):
    teams = sorted({g[s+'Team'] for g in games for s in ('Home', 'Away')})
    ix = {name:i for i,name in enumerate(teams)}
    counts = dict.fromkeys(teams, 0)
    for g in games:
        counts[g['HomeTeam']] += 1; counts[g['AwayTeam']] += 1
    a, b = [], []
    for g in games:
        h, v = g['HomeTeam'], g['AwayTeam']
        w = math.sqrt(2/(counts[h]+counts[v]+2*prior_weight))
        row = np.zeros(len(teams)); row[ix[h]],row[ix[v]] = w,-w
        a.append(row); b.append([w*target(g, name) for name in VARIANTS])
    for name, prior in priors.items():
        if name not in ix:
            continue
        w = math.sqrt(2*prior_weight/(counts[name]+prior_weight))
        row = np.zeros(len(teams)); row[ix[name]]=w
        a.append(row); b.append([w*encode_margin(prior, cap=100)]*len(VARIANTS))
    a.append(np.ones(len(teams))); b.append([0.]*len(VARIANTS))
    coefficients = np.linalg.lstsq(np.array(a), np.array(b), rcond=None)[0]
    return {name: dict(zip(teams,map(float,coefficients[:,i]))) for i,name in enumerate(VARIANTS)}


def metrics(rows, variant):
    y = np.array([r['actual'] for r in rows]); p = np.array([r[variant] for r in rows])
    base = np.array([r['cap28'] for r in rows])
    difference = abs(p-y)-abs(base-y)
    weeks = sorted({r['week'] for r in rows})
    totals=np.array([sum(d for d,r in zip(difference,rows) if r['week']==w) for w in weeks])
    counts=np.array([sum(r['week']==w for r in rows) for w in weeks])
    rng=np.random.default_rng(202510);samples=rng.integers(0,len(weeks),(10000,len(weeks)))
    boot=totals[samples].sum(axis=1)/counts[samples].sum(axis=1)
    return {'games':len(rows),'MAE':float(abs(p-y).mean()),'RMSE':float(np.sqrt(np.mean((p-y)**2))),
            'cappedMarginMAE':float(abs(np.clip(p,-28,28)-np.clip(y,-28,28)).mean()),
            'winnerCorrect':int((np.sign(p)==np.sign(y)).sum()),
            'bias':float((p-y).mean()),'MAEchange':float(difference.mean()),
            'MAEchangeWeekBootstrap95':list(map(float,np.quantile(boot,[.025,.975]))),
            'changedWinnerPicks':int((np.sign(p)!=np.sign(base)).sum())}


def main():
    train_path=ROOT/'archive/2025/cfbweek10.csv'
    test_path=ROOT/'archive/2025/cfbweek15.csv'
    priors_path=ROOT/'archive/2025/MasseyRatings_2024.csv'
    test=[g for g in select_games(read_csv(test_path),2025,99) if int(g['Week'])>10]
    cutoff=min(g['StartDate'] for g in test)
    train=[g for g in select_games(read_csv(train_path),2025,10) if g['StartDate']<cutoff]
    priors={r['Team']:float(r['MasseyRating']) for r in read_csv(priors_path)}
    OUT.mkdir(parents=True,exist_ok=True)
    # Primary and fixed sensitivity run; neither is tuned against holdout results.
    report={'trainGames':len(train),'testGames':len(test),'testWeeks':sorted({int(g['Week']) for g in test}),
            'trainQuarterCoverage':sum(halftime(g) is not None for g in train),
            'trainFBSQuarterCoverage':{k:sum(1 for g in train if g['HomeClassification']=='fbs' and g['AwayClassification']=='fbs' and (k=='total' or halftime(g) is not None)) for k in ['total','valid']},
            'cutoff':cutoff,'inputHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [train_path,test_path,priors_path]},'runs':{}}
    changed=[]
    for g in train:
        if any(target(g,v)!=target(g,'cap28') for v in VARIANTS[1:4]):
            changed.append({'id':g['Id'],'home':g['HomeTeam'],'away':g['AwayTeam'],'week':g['Week'],
                            'homeClass':g['HomeClassification'],'awayClass':g['AwayClassification'],
                            'final':g['HomePoints']-g['AwayPoints'],'halftime':halftime(g),
                            **{v:target(g,v) for v in VARIANTS}})
    for pw in [1.0,.75]:
        fitted=fit_all(train,priors,pw)
        expected=solve(train,priors,prior_weight=pw)
        assert max(abs(expected[n]-fitted['cap28'][n]) for n in expected)<1e-8
        rows=[]; skipped=[]
        for g in test:
            h,a=g['HomeTeam'],g['AwayTeam']
            if h not in expected or a not in expected:
                skipped.append(g['Id']);continue
            home=0 if truth(g.get('NeutralSite')) else 3
            rows.append({'id':g['Id'],'week':int(g['Week']),'home':h,'away':a,
                         'homeClass':g['HomeClassification'],'awayClass':g['AwayClassification'],
                         'actual':g['HomePoints']-g['AwayPoints'],
                         **{v:fitted[v][h]-fitted[v][a]+home for v in VARIANTS}})
        groups={'FBSvsFBS':[r for r in rows if r['homeClass']==r['awayClass']=='fbs'],
                'FBSvsFCS':[r for r in rows if {r['homeClass'],r['awayClass']}=={'fbs','fcs'}],
                'all':rows}
        report['runs'][str(pw)]={'skipped':skipped, 'metrics':{key:{v:metrics(rs,v) for v in VARIANTS} for key,rs in groups.items() if rs}}
        for label,rs in [(f'predictions-prior-{pw}',rows),(f'ratings-prior-{pw}',[{'team':n,**{v:fitted[v][n] for v in VARIANTS}} for n in expected])]:
            with (OUT/f'{label}.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    with (OUT/'changed-training-games.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(changed[0]));w.writeheader();w.writerows(changed)
    (OUT/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
