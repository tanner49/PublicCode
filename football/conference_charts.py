"""Conference visualizations and reproducible neutral-field simulations for weekly publication."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import csv,json,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox,OffsetImage
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
SITE=ROOT/'tanner49.github.io/tanner-ratings'
OUT=SITE/'share/2026/week-05/conferences'
EDITION='2026 Week 5 ? Results through Week 4'
PAPER='#f8f7f1';INK='#173c30';MUTED='#637568'
plt.rcParams.update({'text.parse_math':False,'font.family':'DejaVu Sans'})
SHORT={'American Athletic':'American','Mid-American':'MAC','Mountain West':'Mountain West','Conference USA':'C-USA','FBS Independents':'Independents'}

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=150,facecolor=PAPER)
    fig.savefig(OUT/(name+'.svg'),facecolor=PAPER)
    svg = OUT/(name+'.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n', encoding='utf-8')
    plt.close(fig)

def decorate(fig,title,subtitle):
    fig.patch.set_facecolor(PAPER)
    fig.text(.045,.965,'THE “PROVE IT” RANKINGS',fontsize=14,weight='bold',color=INK)
    fig.text(.045,.918,title,fontsize=28,weight='bold',color=INK)
    fig.text(.045,.88,subtitle,fontsize=11,color=MUTED)
    fig.text(.045,.03,'COLLEGE FOOTBALL',fontsize=11,weight='bold',color=INK)
    fig.text(.96,.03,'2026 Week 5 · Results through Week 4',ha='right',fontsize=10,color=MUTED)

def axis_style(ax):
    ax.set_facecolor(PAPER);ax.tick_params(colors=MUTED)
    for spine in ax.spines.values():spine.set_visible(False)

def main(snapshot_path=None, output=None):
    global OUT, EDITION
    snap_path=Path(snapshot_path) if snapshot_path else SITE/'data/2026/week-05.json'
    snap=json.loads(snap_path.read_text(encoding='utf-8'))
    OUT=Path(output) if output else SITE/'share'/str(snap['season'])/f"week-{snap['week']:02}"/'conferences'
    OUT.mkdir(parents=True,exist_ok=True)
    EDITION=f"{snap['season']} Week {snap['week']} ? Results through Week {snap['throughWeek']}"
    teams=[t for t in snap['teams'] if t['classification']=='fbs']
    groups={name:sorted([t for t in teams if t['conference']==name],key=lambda t:t['rating']) for name in {t['conference'] for t in teams}}
    names=sorted(groups,key=lambda n:-np.median([t['rating'] for t in groups[n]]))
    logos=json.loads((SITE/'logos/index.json').read_text(encoding='utf-8'))
    assert all(t['team'] in logos for t in teams)
    metrics=[]
    for name in names:
        ratings=np.array([t['rating'] for t in groups[name]]);k=max(1,int(np.ceil(len(ratings)/4)))
        metrics.append({'conference':name,'teams':len(ratings),'mean':float(np.mean(ratings)),
                        'median':float(np.median(ratings)),'bottomQuarterMean':float(np.mean(ratings[:k])),
                        'topQuarterMean':float(np.mean(ratings[-k:])), 'quartileGroupSize':k})
    # Chart 1: equal-width conference rows, all team logos, true x positions.
    fig,ax=plt.subplots(figsize=(17,13));fig.subplots_adjust(left=.17,right=.95,bottom=.1,top=.84)
    decorate(fig,'THE CONFERENCE LANDSCAPE','Every FBS team, grouped by conference. Ordered by median rating; vertical ticks mark the middle team strength.')
    axis_style(ax);xmin=min(t['rating'] for t in teams)-5;xmax=max(t['rating'] for t in teams)+5
    ax.set_xlim(xmin,xmax);ax.set_ylim(len(names)-.45,-.6)
    ax.set_yticks(range(len(names)),[f'{SHORT.get(n,n)}  ({len(groups[n])})' for n in names]);ax.tick_params(axis='y',length=0,pad=15,labelsize=12)
    ax.set_xlabel('Prove It rating →',fontsize=13,color=INK,labelpad=15);ax.grid(axis='x',color='#dce2db',zorder=0)
    fig.canvas.draw();pixels_per_rating=ax.get_window_extent().width/(xmax-xmin)
    for i,name in enumerate(names):
        vals=[t['rating'] for t in groups[name]]
        ax.plot([min(vals),max(vals)],[i,i],lw=2,color='#cad5c8',zorder=1)
        ax.plot([np.median(vals)]*2,[i-.34,i+.34],color='#809980',lw=1.2,zorder=1)
        placed=[]
        for t in groups[name]:
            for lane in [0,-.24,.24,-.4,.4]:
                if all(abs(t['rating']-x)*pixels_per_rating>39 or abs(lane-y)>.20 for x,y in placed):break
            placed.append((t['rating'],lane))
            im=Image.open(SITE/logos[t['team']]['path']).convert('RGBA');bbox=im.getbbox()
            if bbox:im=im.crop(bbox)
            im.thumbnail((90,90),Image.Resampling.LANCZOS)
            ax.add_artist(AnnotationBbox(OffsetImage(np.asarray(im),zoom=.20),(t['rating'],i+lane),frameon=False,zorder=3))
    save(fig,'01-conference-distributions')

    # Historical forecast-error bootstrap: no outcomes from 2026.
    source=ROOT/'PublicCode/football/backtests/results/game-by-game.csv'
    with source.open(encoding='utf-8-sig') as f:historical=list(csv.DictReader(f))
    calibration=[r for r in historical if r['bothFBS']=='True' and r['modelAvailable']=='True' and r['period'].startswith('regular') and r['halftime1.25Raw']]
    errors=np.array([float(r['actualHomeMargin'])-float(r['halftime1.25Raw']) for r in calibration])
    rng=np.random.default_rng(20260929);size=1000;matrix=np.full((len(names),len(names)),np.nan);records=[]
    for i,a in enumerate(names):
        for j in range(i+1,len(names)):
            b=names[j];aa=rng.integers(0,len(groups[a]),size=size);bb=rng.integers(0,len(groups[b]),size=size)
            margin=np.array([groups[a][k]['rating'] for k in aa])-np.array([groups[b][k]['rating'] for k in bb])
            # Random orientation makes the residual pool symmetric and zero-mean in expectation.
            noise=rng.choice(errors,size=size)*rng.choice([-1,1],size=size)
            outcomes=margin+noise;ties=outcomes==0
            wins=int(np.sum(outcomes>0)+np.sum(rng.integers(0,2,size=np.sum(ties))))
            matrix[i,j]=wins;matrix[j,i]=size-wins
            records.append({'conferenceA':a,'conferenceB':b,'winsA':wins,'winsB':size-wins,
                            'ratingsOnlyWinsA':int(np.sum(margin>0)),'ratingsOnlyTies':int(np.sum(margin==0)),
                            'averageExpectedMarginA':float(np.mean(margin))})
    fig,ax=plt.subplots(figsize=(15,13));fig.subplots_adjust(left=.18,right=.94,bottom=.14,top=.80)
    decorate(fig,'1,000 GAMES. EVERY CONFERENCE MATCHUP.','Random teams, neutral fields, and historical scoring surprises. Each cell is the row conference’s simulated win–loss record.')
    im=ax.imshow(matrix,cmap='BrBG',vmin=0,vmax=1000,aspect='auto');axis_style(ax)
    ax.set_xticks(range(len(names)),[SHORT.get(n,n) for n in names],rotation=40,ha='right',fontsize=10)
    ax.set_yticks(range(len(names)),[SHORT.get(n,n) for n in names],fontsize=11)
    for i in range(len(names)):
        for j in range(len(names)):
            if i==j:text='—';color=MUTED
            else:
                w=int(matrix[i,j]);text=f'{w}–{1000-w}';color='white' if w<200 or w>800 else '#173c30'
            ax.text(j,i,text,ha='center',va='center',fontsize=9,color=color,weight='bold')
    ax.set_xticks(np.arange(-.5,len(names),1),minor=True);ax.set_yticks(np.arange(-.5,len(names),1),minor=True)
    ax.grid(which='minor',color=PAPER,lw=3);ax.tick_params(which='both',length=0)
    fig.text(.18,.075,'Green = row conference favored · Brown = opponent favored · Illustrative simulations, not calibrated win probabilities',fontsize=9,color=MUTED)
    save(fig,'02-conference-matchups')

    # Chart 3: depth without over-weighting conference membership size.
    fig,ax=plt.subplots(figsize=(15,10));fig.subplots_adjust(left=.17,right=.95,bottom=.14,top=.81)
    decorate(fig,'POWER AT THE TOP. STRENGTH THROUGH THE ROSTER.','Each line runs from the average of a conference’s bottom quarter to its top quarter. The dark dot marks its median.')
    axis_style(ax)
    for i,m in enumerate(metrics):
        ax.plot([m['bottomQuarterMean'],m['topQuarterMean']],[i,i],lw=6,color='#ccd9cd',solid_capstyle='round')
        ax.scatter(m['bottomQuarterMean'],i,s=100,color='#be8e53',zorder=3)
        ax.scatter(m['topQuarterMean'],i,s=100,color='#428572',zorder=3)
        ax.scatter(m['median'],i,s=65,color=INK,zorder=4)
        ax.text(m['bottomQuarterMean']-1.5,i,f"{m['bottomQuarterMean']:.1f}",ha='right',va='center',color=MUTED,fontsize=10)
        ax.text(m['topQuarterMean']+1.5,i,f"{m['topQuarterMean']:.1f}",ha='left',va='center',color=MUTED,fontsize=10)
    ax.set_yticks(range(len(names)),[SHORT.get(n,n) for n in names]);ax.invert_yaxis();ax.tick_params(axis='y',length=0)
    ax.set_xlim(min(m['bottomQuarterMean'] for m in metrics)-9,max(m['topQuarterMean'] for m in metrics)+9)
    ax.grid(axis='x',color='#dce2db');ax.set_axisbelow(True);ax.set_xlabel('Prove It rating →',fontsize=13,color=INK)
    for color,label in [('#be8e53','Bottom-quarter average'),(INK,'Conference median'),('#428572','Top-quarter average')]:ax.scatter([],[],color=color,label=label)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.085),ncol=3,frameon=False)
    save(fig,'03-conference-depth')

    for name,rs in [('conference-strength',metrics),('simulated-records',records)]:
        with (OUT/(name+'.csv')).open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
    with (OUT/'team-ratings.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['team','conference','rating','divisionRank'],extrasaction='ignore');w.writeheader();w.writerows(teams)
    (OUT/'simulation-method.json').write_text(json.dumps({'seed':20260929,'gamesPerPair':1000,'conferencePairs':len(records),
       'sampling':'uniform teams within each conference, with replacement; each pair simulated once; reverse records exactly complementary',
       'outcome':'current rating difference + randomly sampled historical forecast error, randomly sign-flipped; no home advantage',
       'historicalErrorGames':len(errors),'historicalErrorRMS':float(np.sqrt(np.mean(errors**2))),
       'calibrationScope':'all available 2023-2025 regular-season FBS/FBS forecasts in saved backtest, including games without usable book lines; no 2026 outcomes',
       'snapshotSha256':hashlib.sha256(snap_path.read_bytes()).hexdigest(),'historicalSha256':hashlib.sha256(source.read_bytes()).hexdigest()},indent=2)+'\n')
    (OUT/'README.md').write_text(f'''# Conference previews — 2026 Week 5

All {len(teams)} rated FBS teams, assigned to the conferences in the supplied snapshot. Independents are a comparison group, not an actual conference. Charts use the selected publication and do not change its team ratings.

1. **Conference distributions:** every team logo at its actual rating; vertical staggering prevents collisions and carries no meaning. Conferences ordered by median rating. Tick marks indicate medians.
2. **1,000-game matchups:** {len(records)} conference pairs, 1,000 games per pair, seed 20260929. Sample each team with equal probability within its conference, with replacement. Neutral-field expected margin is the rating difference. Add a sampled forecast error from {len(errors)} available regular-season FBS-vs-FBS forecasts from the 2023–2025 backtest, randomly sign-flipped to avoid home/away orientation bias. Score ties, if any, get a fair coin winner. Each matchup is simulated once; the reverse cell is exactly complementary. No bookmaker line is used for simulated outcomes. The noise pool has RMS {np.sqrt(np.mean(errors**2)):.2f} points. No parameters were tuned to produce desired conference results.

The historical errors include model uncertainty, not just intrinsic randomness. A shared symmetric error distribution is a simplifying assumption; it ignores matchup-specific variance, spread-dependent errors, roster changes, and correlated results. These are illustrative simulations, **not calibrated win probabilities** or literal future schedules. Monte Carlo variation alone is roughly ±31 wins at a 50% rate in 1,000 independent draws; total modeling uncertainty is greater. Random pairings do not guarantee a balanced result. `ratingsOnlyWinsA` in the CSV shows automatic higher-rating-wins results for the exact same sampled pairings, without upset noise.

3. **Conference depth:** average top quarter and bottom quarter (round group size up), plus median. Conference size is not a strength bonus. Independents have only two teams, so their endpoints each represent one team.

All charts include PNG and SVG copies. Logos reuse the website's ESPN-sourced school assets; trademarks belong to their owners. All plotted values, simulation settings, and hashes are saved here. Reproduce from the football directory with `python conference_charts.py` (or publish the latest snapshot with `python share_cards.py`).
''',encoding='utf-8')
    cards=''.join(f'<section><h2>{title}</h2><a href="{name}.png"><img src="{name}.png" alt="{title}"></a><p><a href="{name}.png" download>PNG</a> · <a href="{name}.svg" download>SVG</a></p></section>' for name,title in [('01-conference-distributions','Conference distributions — every FBS team'),('02-conference-matchups','1,000 games per conference matchup'),('03-conference-depth','Conference strength and depth')])
    (OUT/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Prove It — conference previews</title><style>body{max-width:1400px;margin:40px auto;padding:0 20px;background:#f8f7f1;color:#173c30;font:16px system-ui}img{width:100%;height:auto}section{margin:50px 0}a{color:inherit}</style><h1>Conference previews</h1><p>2026 Week 5 · Local files · <a href="README.md">Methods and assumptions</a></p>'+cards+'</html>',encoding='utf-8')
    assert all(r['winsA']+r['winsB']==1000 for r in records) and len(records)==len(names)*(len(names)-1)//2
    print('Saved',OUT,'noise pool',len(errors),'RMS',round(np.sqrt(np.mean(errors**2)),2))

if __name__=='__main__':main()
