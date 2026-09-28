"""Local descriptive weekly analysis; no model refits or selection."""
from backtest import *
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

DEST=ROOT/'week-results'

def label(r):
    return int(r['period'].split('-')[1]) if r['period'].startswith('regular') else 'Postseason'

def phase(r):
    w=label(r)
    if w=='Postseason':return 'Postseason'
    if w<=7:return 'Weeks 4-7'
    if w<=10:return 'Weeks 8-10'
    if w<=14:return 'Weeks 11-14'
    return 'Weeks 15-16'

def main():
    DEST.mkdir(exist_ok=True)
    allrows=read_csv(OUT/'game-by-game.csv')
    rows=[r for r in allrows if r['lineStatus']=='explicit_close' and truth(r['modelAvailable'])]
    weeks=[];phases=[]
    for group,fn,labels in [(weeks,label,[*range(4,17),'Postseason']),
                            (phases,phase,['Weeks 4-7','Weeks 8-10','Weeks 11-14','Weeks 15-16','Postseason'])]:
        for lab in labels:
            for year in ['all','2023','2024','2025']:
                rs=[r for r in rows if fn(r)==lab and (year=='all' or r['season']==year)]
                supplied=[r for r in allrows if fn(r)==lab and (year=='all' or r['season']==year)]
                group.append({'period':lab,'season':year,'eligibleSupplied':len(supplied),**summary(rs),
                              'rawProfit':summary(rs,raw=True)['profit']})
    assert sum(s['profit'] for s in weeks if s['season']=='all')==-6140
    write_csv(DEST/'weekly.csv',weeks);write_csv(DEST/'phases.csv',phases)
    (DEST/'summary.json').write_text(json.dumps({'weeks':weeks,'phases':phases},indent=2)+'\n')
    # Trend estimate is descriptive only, with no optimized week cutoff.
    trend={}
    for year in ['all','2023','2024','2025']:
        rs=[r for r in rows if isinstance(label(r),int) and label(r)<=14 and r['halftime1.25Result'] in ['W','L'] and (year=='all' or r['season']==year)]
        x=np.array([label(r) for r in rs]);y=np.array([r['halftime1.25Result']=='W' for r in rs],dtype=float)
        trend[year]={'bets':len(rs),'linearWinRateChangePerWeek':float(np.polyfit(x,y,1)[0])}
    (DEST/'descriptive-trend.json').write_text(json.dumps(trend,indent=2)+'\n')
    def table(records):
        ls=['| Week / phase | W-L | Win rate | Profit | ROI |','|---|---:|---:|---:|---:|']
        for s in records:
            rate=f"{s['winRate']*100:.2f}%" if s['winRate'] is not None else 'N/A'
            roi=f"{s['ROI']*100:+.2f}%" if s['ROI'] is not None else 'N/A'
            ls.append(f"| {s['period']} | {s['wins']}-{s['losses']} | {rate} | ${s['profit']:+,} | {roi} |")
        return ls
    lines=['# Production model by betting week','',
           'Frozen halftime1.25 production model; same explicit-close sample and $110 stake / $100 win. No bets before Week 4; +3 home (neutral 0); prior fades to zero by Week 8. Betting week is the week being predicted, not the final training week. No model refits or settings changes.','',
           '## Pooled weeks','',*table([s for s in weeks if s['season']=='all']),'',
           '## Season phases','',*table([s for s in phases if s['season']=='all'])]
    for year in ['2023','2024','2025']:
        lines+=['',f'## {year} phases','',*table([s for s in phases if s['season']==year])]
    lines+=['','## Coverage and interpretation','',
            '- 2023 Week 4 has zero usable explicit closing lines under the existing quality filter; its malformed/current-only lines remain excluded. Week 4 therefore pools 2024 and 2025 only. `weekly.csv` shows supplied and matched counts by year.',
            '- 2025 supplied completed FBS games end at Week 14. Weeks 15-16 have very few games and differing calendar coverage; postseason is separate. Week numbering follows the supplied season exports.',
            '- Weeks 4-7, 8-10, and 11-14 were chosen before inspecting this breakdown. No best start-week strategy is selected. The previous conversation already examined late-season splits, so these are exploratory summaries, not new holdout evidence.',
            '- Better results late can reflect more data, prior decay, changing opponents/game mix or chance; this table cannot identify the cause. Results share teams and are not independent draws.',
            '- Archived handicap and hypothetical -110 pricing limitations are unchanged. Exact no-edge picks are skipped. Raw-prediction profitability is included as a sensitivity column.',
            '',f"Input SHA-256: `{digest(OUT/'game-by-game.csv')}`. Reproduce with `python week_analysis.py`. Everything remains local."]
    (DEST/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    pooled=[s for s in weeks if s['season']=='all' and isinstance(s['period'],int) and s['period']<=14]
    axes[0].plot([s['period'] for s in pooled],[100*s['winRate'] for s in pooled],marker='o',color='#345e7b')
    axes[0].set(title='Win rate by forecast week (pooled)',xlabel='Betting week',ylabel='ATS win rate')
    labs=['Weeks 4-7','Weeks 8-10','Weeks 11-14']
    for year,color in [('2023','#b65543'),('2024','#a57e2e'),('2025','#397e65')]:
        ss=[next(s for s in phases if s['season']==year and s['period']==p) for p in labs]
        axes[1].plot(range(3),[100*s['winRate'] for s in ss],marker='o',label=year,color=color)
    axes[1].set_xticks(range(3),labs);axes[1].set_title('Does improvement repeat each season?');axes[1].legend(frameon=False)
    for ax in axes:
        ax.axhline(110/210*100,color='#555',ls='--',lw=1);ax.yaxis.set_major_formatter(PercentFormatter(100));ax.spines[['top','right']].set_visible(False);ax.set_ylim(35,70)
    fig.suptitle('Production model: performance as the season progresses',fontsize=15)
    fig.text(.5,.015,'Dashed line: 52.38% break-even | 2023 Week 4 lacks usable closing lines | 2025 through Week 14 | Descriptive, not independent validation',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(DEST/'weekly-performance.png',dpi=170)
    print('\n'.join(lines[:42]));print('PHASES',json.dumps(phases))

if __name__=='__main__':main()
