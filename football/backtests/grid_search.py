"""Local 25-point sparse factorial search plus ten axial refinements."""
from backtest import *
import numpy as np
import shutil

SEARCH = ROOT/'grid-results'
BASE = dict(bonus=2.75,cap=28.0,multiplier=1.25,decayStart=4,decayStep=.25)

def weight(config,label):
    if not label.startswith('regular'):
        return 0.
    return max(0.,1.-max(0,int(label.split('-')[1])-config['decayStart'])*config['decayStep'])

def targets(games,c):
    out=[]
    for g in games:
        final=g['HomePoints']-g['AwayPoints'];half=halftime_margin(g)
        credit=min(abs(final),c['cap'])
        if half is not None and half*final>0 and abs(half)>=21 and abs(final)>=10:
            credit=max(credit,min(56,c['multiplier']*abs(half)))
        out.append(math.copysign(credit+c['bonus'],final) if final else 0.)
    return np.array(out)

def fit_batch(games,priors,configs,pweight):
    names=sorted({g[s+'Team'] for g in games for s in ('Home','Away')})
    index={n:i for i,n in enumerate(names)};n=len(names)
    h=np.array([index[g['HomeTeam']] for g in games]);a=np.array([index[g['AwayTeam']] for g in games])
    counts=np.bincount(np.concatenate([h,a]),minlength=n)
    w=np.sqrt(2/(counts[h]+counts[a]+2*pweight))
    A=np.zeros((len(games)+n+1,n));ids=np.arange(len(games))
    A[ids,h]=w;A[ids,a]=-w;A[-1,:]=1
    B=np.zeros((len(A),len(configs)))
    for j,c in enumerate(configs):
        B[:len(games),j]=targets(games,c)*w
        for team,prior in priors[c['id']].items():
            if team not in index or not pweight:continue
            i=index[team];pw=math.sqrt(2*pweight/(counts[i]+pweight))
            A[len(games)+i,i]=pw
            B[len(games)+i,j]=(math.copysign(min(abs(prior),100)+c['bonus'],prior) if prior else 0)*pw
    # Prior membership is the same across candidates; changing values only changes RHS.
    assert len({tuple(sorted(priors[c['id']])) for c in configs})==1
    values=np.linalg.lstsq(A,B,rcond=None)[0]
    return {c['id']:dict(zip(names,map(float,values[:,j]))) for j,c in enumerate(configs)}

def coarse():
    bonus=[0,1.5,2.75,4,6];cap=[21,28,35,42,56];mult=[0,1,1.25,1.5,2]
    schedules=[(3,.5),(3,.25),(4,.25),(5,.25),(5,.125)]
    result=[dict(id='C00',stage='coarse',**BASE)]
    # Orthogonal-array construction covers broad pairwise combinations in 25 runs.
    # Replace its first row with production baseline: 24 array points + baseline.
    for a in range(5):
        for b in range(5):
            if a==b==0:continue
            start,step=schedules[(a+2*b)%5]
            result.append(dict(id=f'C{len(result):02}',stage='coarse',bonus=bonus[a],cap=cap[b],
                               multiplier=mult[(a+b)%5],decayStart=start,decayStep=step))
    assert len(result)==25
    return result

def refine(best,old):
    result=[];seen={tuple(c[k] for k in BASE) for c in old}
    for key,step,low,high in [('bonus',.75,0,8),('cap',3.5,14,63),('multiplier',.125,0,2.5),
                              ('decayStart',1,2,7),('decayStep',.0625,.0625,1)]:
        for direction in [-1,1]:
            for offset in [direction,2*direction,-direction,-2*direction,3*direction,-3*direction]:
                c={k:best[k] for k in BASE};c[key]=c[key]+offset*step
                signature=tuple(c[k] for k in BASE)
                if low<=c[key]<=high and signature not in seen:
                    c.update(id=f'R{len(result)+1:02}',stage='refine');result.append(c);seen.add(signature);break
            else:raise ValueError('No distinct neighbor')
    return result

def metric(rows):
    return summary(rows,model='model')

def rank_key(s):
    return (s['profit'],s['ROI'],min(s[f'profit{y}'] for y in (2023,2024,2025)))

def evaluate(configs,stage):
    seasons={y:load_games(y) for y in (2023,2024,2025)}
    audits=json.loads((OUT/'weekly-audit.json').read_text())
    original=read_csv(OUT/'game-by-game.csv')
    eligible={r['id']:r for r in original if r['lineStatus']=='explicit_close' and r['modelAvailable']=='True'}
    bootstrap={r['id']:float(r['rating']) for r in read_csv(OUT/'prior-2023.csv')}
    prev={c['id']:bootstrap for c in configs};bets={c['id']:[] for c in configs}
    for year,games in seasons.items():
        byid={g['Id']:g for g in games}
        names_ids={g[s+'Team']:g[s+'Id'] for g in games for s in ('Home','Away')}
        priors={c['id']:{n:prev[c['id']][i] for n,i in names_ids.items() if i in prev[c['id']]} for c in configs}
        for audit in [a for a in audits if a['season']==year]:
            label=audit['period'];train=[byid[i] for i in audit['trainIds']]
            assert max(stamp(g['StartDate'])+timedelta(hours=12) for g in train)<stamp(audit['cutoff'])
            groups=collections.defaultdict(list)
            for c in configs:groups[weight(c,label)].append(c)
            fits={}
            for pw,group in groups.items():fits.update(fit_batch(train,priors,group,pw))
            names=sorted(next(iter(fits.values())))
            np.savez_compressed(SEARCH/'weekly-ratings'/f'{stage}-{year}-{label}.npz',
                                teams=np.array(names),models=np.array([c['id'] for c in configs]),
                                ratings=np.array([[fits[c['id']][n] for n in names] for c in configs]),
                                weights=np.array([weight(c,label) for c in configs]))
            for ident in audit['fixtures']:
                if ident not in eligible:continue
                r=eligible[ident];g=byid[ident]
                for c in configs:
                    ratings=fits[c['id']];raw=ratings[g['HomeTeam']]-ratings[g['AwayTeam']]+(0 if truth(g['NeutralSite']) else 3)
                    prediction=half_round(raw);market=float(r['marketHomeMargin']);actual=float(r['actualHomeMargin'])
                    bets[c['id']].append(dict(modelId=c['id'],season=year,period=label,id=ident,date=r['date'],
                        home=r['home'],away=r['away'],bothFBS=r['bothFBS'],marketHomeMargin=market,actualHomeMargin=actual,
                        priorWeight=weight(c,label),prediction=prediction,rawPrediction=raw,
                        modelResult=grade(prediction,market,actual),rawResult=grade(raw,market,actual)))
            print(stage,year,label,'fit groups',len(groups),flush=True)
        # Recompute prior-season final ratings for each candidate, never with current-year games.
        if year<2025:
            finals=fit_batch(games,{c['id']:{} for c in configs},configs,0)
            # The inherited prior encoder adds +/-bonus to any nonzero value.
            # Snap numerical zero before encoding, so SVD roundoff cannot add a bonus.
            prev={c['id']:{names_ids[n]:(0. if abs(v)<1e-9 else v) for n,v in finals[c['id']].items()} for c in configs}
            write_csv(SEARCH/f'{stage}-priors-{year+1}.csv',
                      [{'modelId':c['id'],'team':n,'id':names_ids[n],'rating':prev[c['id']][names_ids[n]]} for c in configs for n,v in finals[c['id']].items()])
    leaderboard=[]
    for c in configs:
        rows=sorted(bets[c['id']],key=lambda r:(r['date'],r['id']))
        assert len(rows)==1858
        write_csv(SEARCH/'bets'/f'{c["id"]}.csv',rows)
        stats={**c,**metric(rows)}
        for y in (2023,2024,2025):
            ys=metric([r for r in rows if r['season']==y])
            for k in ['profit','wins','losses','ROI','winRate']:stats[k+str(y)]=ys[k]
        raw=metric([{**r,'modelResult':r['rawResult']} for r in rows])
        stats.update(rawProfit=raw['profit'],rawWinRate=raw['winRate'],rawROI=raw['ROI'])
        leaderboard.append(stats)
        if c['id']=='C00':
            for r in rows:
                old=eligible[r['id']]
                assert abs(r['rawPrediction']-float(old['halftime1.25Raw']))<1e-7
                assert r['modelResult']==old['halftime1.25Result']
    return sorted(leaderboard,key=rank_key,reverse=True)

def main():
    SEARCH.mkdir(exist_ok=True);(SEARCH/'bets').mkdir(exist_ok=True);(SEARCH/'weekly-ratings').mkdir(exist_ok=True)
    first=coarse()
    plan={'objective':'maximize total $ profit over 2023-2025; ties ROI then worst-year profit',
          'coarse':first,'refinement':'ten axial neighbors of coarse winner; bonus +/-0.75, cap +/-3.5, multiplier +/-0.125, start +/-1 week, decay +/-0.0625; inward neighbors at bounds',
          'fixed':'same 1858 explicit-close games; +3 HFA, neutral 0; half lead>=21, final win>=10, half credit<=56; $110 risk, +$100 win; no edge passes',
          'priors':'fixed 2022 bootstrap for all 2023 runs; candidate-specific prior-year final for 2024/2025; winner bonus also affects existing prior encoding',
          'priorFormula':'max(0,1-max(0,forecastWeek-decayStart)*decayStep); postseason 0',
          'validation':'all three seasons used for selection, not an out-of-sample performance claim',
          'inputHashes':{str(p.relative_to(ROOT)):digest(p) for p in [OUT/'game-by-game.csv',OUT/'weekly-audit.json',OUT/'prior-2023.csv',ROOT/'production_ratings.py',ROOT/'grid_search.py']}}
    (SEARCH/'search-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    board=evaluate(first,'coarse');write_csv(SEARCH/'coarse-leaderboard.csv',board)
    print('COARSE WINNER',json.dumps(board[0]),flush=True)
    second=refine(board[0],first)
    (SEARCH/'refinement-plan.json').write_text(json.dumps(second,indent=2)+'\n')
    board+=evaluate(second,'refine');board.sort(key=rank_key,reverse=True)
    write_csv(SEARCH/'leaderboard.csv',board)
    (SEARCH/'leaderboard.json').write_text(json.dumps(board,indent=2)+'\n')
    print('FINAL TOP FIVE',json.dumps(board[:5],indent=2),flush=True)

if __name__=='__main__':main()
