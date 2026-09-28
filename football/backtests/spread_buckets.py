"""Private descriptive spread-bucket analysis of the frozen production model."""
from backtest import *

DEST=ROOT/'spread-bucket-results'
LABELS=['0-<5','5-<10','10-<15','15-<20','20-<25','25+']

def bucket(spread):
    return LABELS[min(int(abs(spread)//5),5)]

def stats(rows):
    s=summary(rows)
    wins,losses=s['wins'],s['losses'];n=wins+losses;p=110/210
    # Descriptive iid benchmark only; shared teams make bets dependent.
    tail=sum(math.exp(math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)+k*math.log(p)+(n-k)*math.log1p(-p)) for k in range(wins,n+1)) if n else None
    bets=[r for r in rows if r['halftime1.25Result']!='PASS']
    dogs=sum(float(r['marketHomeMargin'])*(float(r['halftime1.25Prediction'])-float(r['marketHomeMargin']))<0 for r in bets)
    return {**s,'underdogPicks':dogs,'favoritePicks':len(bets)-dogs-sum(float(r['marketHomeMargin'])==0 for r in bets),
            'pAboveBreakevenIID':tail,'pBonferroniSixBuckets':min(1,6*tail) if tail is not None else None}

def main():
    DEST.mkdir(exist_ok=True)
    rows=[r for r in read_csv(OUT/'game-by-game.csv') if r['lineStatus']=='explicit_close' and truth(r['modelAvailable'])]
    assert len(rows)==1858
    for r in rows:r['spreadBucket']=bucket(float(r['homeSpread']))
    summaries=[]
    for label in LABELS:
        selected=[r for r in rows if r['spreadBucket']==label]
        for year in ['all','2023','2024','2025']:
            rs=[r for r in selected if year=='all' or r['season']==year]
            summaries.append({'bucket':label,'season':year,**stats(rs)})
    assert sum(r['profit'] for r in summaries if r['season']=='all')==-6140
    write_csv(DEST/'buckets.csv',summaries)
    (DEST/'buckets.json').write_text(json.dumps(summaries,indent=2)+'\n')
    raw=[{'bucket':label,**summary([r for r in rows if r['spreadBucket']==label],raw=True)} for label in LABELS]
    write_csv(DEST/'unrounded-sensitivity.csv',raw)
    sides=[]
    for label in LABELS:
        for side in ['underdog','favorite']:
            rs=[]
            for r in rows:
                if r['spreadBucket']!=label or r['halftime1.25Result']=='PASS':continue
                value=float(r['marketHomeMargin'])*(float(r['halftime1.25Prediction'])-float(r['marketHomeMargin']))
                if (side=='underdog' and value<0) or (side=='favorite' and value>0):rs.append(r)
            sides.append({'bucket':label,'pickSide':side,**summary(rs)})
    write_csv(DEST/'favorite-underdog.csv',sides)
    lines=['# Production model: bookmaker spread buckets','',
           'Same frozen production halftime1.25 model; no refits or optimization. Absolute bookmaker handicap, not the model prediction or model-market edge. Boundaries are lower-inclusive, upper-exclusive; exactly 5 belongs to 5-<10; exactly 25 belongs to 25+.','',
           '2023-2025 combined; 2025 through Week 14. Same explicit-close sample, Week 4 onward, +3 home (neutral 0), decaying prior, hypothetical -110 pricing, $110 risk/$100 win. Exact no-edge predictions are passed. All work remains local.','',
           '| Absolute spread | W-L | Passes | Win rate | Profit | ROI | 95% win-rate interval |','|---|---:|---:|---:|---:|---:|---|']
    for s in summaries:
        if s['season']!='all':continue
        lo,hi=s['winRateWilson95']
        lines.append(f"| {s['bucket']} | {s['wins']}-{s['losses']} | {s['passes']} | {100*s['winRate']:.2f}% | ${s['profit']:+,} | {100*s['ROI']:+.2f}% | {100*lo:.1f}%-{100*hi:.1f}% |")
    lines+=['','## Profit by year','', '| Absolute spread | 2023 | 2024 | 2025 through W14 |','|---|---:|---:|---:|']
    for label in LABELS:
        ss={s['season']:s for s in summaries if s['bucket']==label}
        lines.append('| '+label+' | '+' | '.join(f"${ss[y]['profit']:+,} ({100*ss[y]['winRate']:.1f}%)" for y in ['2023','2024','2025'])+' |')
    lines+=['','## Interpretation safeguards','',
            '- Six buckets are exploratory subgroup checks of already-inspected seasons. A profitable bucket alone does not establish a repeatable strategy.',
            '- The JSON/CSV includes one-sided binomial tail probabilities against the -110 break-even rate (52.38%), and a six-comparison Bonferroni correction. These are only iid benchmarks; shared teams and weeks create dependence. They do not correct for every earlier analysis we have tried.',
            '- `unrounded-sensitivity.csv` uses unrounded predictions, avoiding pass changes from display rounding. `favorite-underdog.csv` separates picks by side as a descriptive check, not a separately optimized strategy.',
            '- Line provenance and coverage limitations from the original backtest still apply; missing/malformed lines are excluded consistently.','',
            f"Source SHA-256: `{digest(OUT/'game-by-game.csv')}`. Reproduce with `python spread_buckets.py`."]
    (DEST/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps([s for s in summaries if s['season']=='all'],indent=2))
    print('YEARLY',[(s['bucket'],s['season'],s['profit']) for s in summaries if s['season']!='all'])

if __name__=='__main__':main()
