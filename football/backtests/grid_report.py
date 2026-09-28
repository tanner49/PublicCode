from grid_search import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
plt.rcParams['text.parse_math']=False

def money(v):return ('-' if v<0 else '+')+f'${abs(v):,}'
def pct(v):return f'{100*v:.2f}%'

def main():
    board=json.loads((SEARCH/'leaderboard.json').read_text());best=board[0]
    baseline=next(r for r in board if r['id']=='C00')
    coarsebest=max((r for r in board if r['stage']=='coarse'),key=rank_key)
    positive=sum(r['profit']>0 for r in board)
    profitable_all=sum(all(r[f'profit{y}']>0 for y in (2023,2024,2025)) for r in board)
    bets=read_csv(SEARCH/'bets'/f'{best["id"]}.csv')
    lines=['# Private parameter search: 25 broad candidates + 10 refinements','',
           f"Best tested candidate: **{best['id']}**, {best['wins']}-{best['losses']} ({pct(best['winRate'])}), **{money(best['profit'])}**, {pct(best['ROI'])} ROI. Baseline: {money(baseline['profit'])}, {pct(baseline['winRate'])}.",'',
           '**All three years were used to choose the parameters. These are optimized in-sample results, not an independently validated edge.** No deployment, commit, or push was performed.','',
           '## Selected settings','', '| Parameter | Baseline | Best tested |','|---|---:|---:|',
           f"| Winner bonus | 2.75 | {best['bonus']} |",f"| Final-margin cap | 28 | {best['cap']} |",
           f"| Halftime multiplier | 1.25 | {best['multiplier']} |",f"| Prior decay (start, step) | (4, .25) | ({best['decayStart']}, {best['decayStep']}) |",'',
           'The prior weight for forecast week W is `max(0, 1 - max(0, W-start)*step)`. Start means the last week at full weight; the first decrement is the following week. Postseason weight stays zero.','',
           '| Forecast week | Baseline prior | Best prior |','|---|---:|---:|']
    for w in range(4,14):lines.append(f"| {w} | {weight(BASE,f'regular-{w:02}'):g} | {weight(best,f'regular-{w:02}'):g} |")
    lines+=['','## Year-by-year results','', '| Season | Baseline profit | Best W-L | Best win rate | Best profit | Best ROI |','|---|---:|---:|---:|---:|---:|']
    for y in (2023,2024,2025):
        lines.append(f"| {y}{' (through Week 14)' if y==2025 else ''} | {money(baseline[f'profit{y}'])} | {best[f'wins{y}']}-{best[f'losses{y}']} | {pct(best[f'winRate{y}'])} | {money(best[f'profit{y}'])} | {pct(best[f'ROI{y}'])} |")
    lines+=['',f"The winning candidate risked ${best['risked']:,} over {best['wins']+best['losses']+best['pushes']} bets and passed {best['passes']} exact no-edge games. Unrounded predictions, betting every matched game, returned {money(best['rawProfit'])} ({pct(best['rawWinRate'])}; ROI {pct(best['rawROI'])}).",'',
            f"{positive}/35 candidates were profitable overall; {profitable_all}/35 were profitable in every season. The best coarse candidate was {coarsebest['id']} at {money(coarsebest['profit'])}; refinement changed the best profit by {money(best['profit']-coarsebest['profit'])}.",'',
            '## Top ten tested candidates','', '| ID | Bonus | Cap | Half multiplier | Decay start / step | W-L | Win rate | Profit | ROI |','|---|---:|---:|---:|---|---:|---:|---:|---:|']
    for r in board[:10]:lines.append(f"| {r['id']} | {r['bonus']} | {r['cap']} | {r['multiplier']} | {r['decayStart']} / {r['decayStep']} | {r['wins']}-{r['losses']} | {pct(r['winRate'])} | {money(r['profit'])} | {pct(r['ROI'])} |")
    lines+=['','## Method and limits','',
            '- Sparse factorial design: 24 points from a five-level orthogonal array, plus the production baseline. This is a broad 25-model sample, not an exhaustive Cartesian product. Bonus levels: 0, 1.5, 2.75, 4, 6. Cap levels: 21, 28, 35, 42, 56. Halftime levels: 0, 1, 1.25, 1.5, 2. Prior schedules: (3,.5), (3,.25), (4,.25), (5,.25), (5,.125). A zero multiplier removes the halftime adjustment.',
            '- Ten refinements around the coarse winner: each numerical coordinate one step down and up. Steps: bonus .75; cap 3.5; multiplier .125; decay start 1 week; decay rate .0625. At a bound, use distinct inward neighbors. Refinement settings were saved before evaluating them. A limited search finds the best tested setting, not a proven global or local maximum.',
            '- Objective fixed before evaluation: pooled dollar profit at $110 risk / $100 win; ties broken by ROI, then worst-year profit. No model changes based on individual game results.',
            '- Same 1,858 ESPN-labeled closing-line games, 47 chronological forecast periods, +3 home advantage, neutral-site 0, half-point prediction rounding, and exact no-edge passes. Same guarded halftime rule: winner led by at least 21 at half and won by at least 10; half-credit ceiling 56. Those guardrails were not tuned.',
            '- 2023 uses the same frozen 2022 bootstrap for every candidate. For 2024/2025, regenerate the prior from the preceding season using that candidate\'s parameters. Winner bonus also changes the inherited prior encoding. Prior values within 1e-9 of zero are snapped to zero to avoid a floating-point sign triggering a spurious bonus.',
            '- Ratings were fit before each period with the original audited training IDs and 12-hour completion buffer. Candidates sharing the same prior weight are solved together with separate target vectors; this is numerically equivalent to separate least-squares fits. The baseline is asserted to reproduce every prior prediction within 1e-7 and every ATS result exactly.',
            '- Model selection uses outcomes from all three years, so the selected configuration has selection bias despite temporally clean ratings. The apparent win rate is optimistically selected. 2025 also informed earlier model development. A new future sample is needed to test the selected model.',
            '- Historical-line limitations from the original report remain: API-labeled closes lack independent capture timestamps; actual juice varied, while this experiment assumes -110 universally. 2025 supplied FBS results stop at Week 14. No odds-source changes or extra filters were selected to improve results.',
            '', '## Saved locally','',
            '- `grid-results/leaderboard.csv` and `.json`: all 35 configurations, per-year results and unrounded sensitivity.',
            '- `grid-results/search-plan.json`, `refinement-plan.json`: design, objective, settings and input hashes.',
            '- `grid-results/bets/`: a complete game ledger for every candidate.',
            '- `grid-results/weekly-ratings/`: compressed NumPy archives containing team names, candidate IDs, ratings and prior weights for every period.',
            '- `results/weekly-audit.json`: shared exact training IDs and cutoffs.',
            '- `grid_search.py`, `test_grid_search.py`, `grid_report.py`: reproducible implementation, checks and report generation.',
            '', 'Run `python grid_search.py`, `python -m unittest test_grid_search -v`, then `python grid_report.py`. Everything stays in this private local folder.']
    (SEARCH/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for stage,color in [('coarse','#557c99'),('refine','#b17838')]:
        rs=[r for r in board if r['stage']==stage]
        axes[0].scatter([board.index(r)+1 for r in rs],[r['profit'] for r in rs],color=color,label=stage,s=38)
    axes[0].axhline(0,color='#666',lw=.8);axes[0].axhline(baseline['profit'],color='#999',ls='--',label='Baseline')
    axes[0].set(xlabel='Rank by pooled historical profit',ylabel='Profit at $110 per bet',title='All 35 tested configurations');axes[0].legend(frameon=False)
    x=np.arange(3)
    axes[1].bar(x-.18,[baseline[f'profit{y}'] for y in (2023,2024,2025)],.36,label='Baseline',color='#557c99')
    axes[1].bar(x+.18,[best[f'profit{y}'] for y in (2023,2024,2025)],.36,label=f"Selected {best['id']}",color='#b17838')
    axes[1].set_xticks(x,['2023','2024','2025*']);axes[1].axhline(0,color='#666',lw=.8);axes[1].set_title('Selected parameters by season');axes[1].legend(frameon=False)
    for ax in axes:
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'${v:,.0f}'));ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Prove It parameter search: optimized historical results',fontsize=15)
    fig.text(.02,.015,'All years used for selection; not held-out evidence. *2025 through Week 14. Hypothetical -110 pricing.',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(SEARCH/'search-results.png',dpi=170)
    print(json.dumps({'best':best,'coarseBest':coarsebest['id'],'profitable':positive,'profitableAllYears':profitable_all},indent=2))

if __name__=='__main__':main()
