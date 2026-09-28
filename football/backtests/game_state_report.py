from game_state_backtest import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
plt.rcParams['text.parse_math']=False

LABELS={'C00':'Current halftime model','OT':'Current model + OT treatment','CAP':'Cap28 + OT treatment',
        'SOFT':'Soft cap + OT treatment','STATE_CAP':'Game-state + hard cap + OT',
        'STATE_SOFT':'Game-state + soft cap + OT (primary)'}
def money(x):return ('-' if x<0 else '+')+f'${abs(x):,}'
def pct(x):return f'{100*x:.2f}%'

def main():
    board=json.loads((STATE_OUT/'leaderboard.json').read_text());stats={r['id']:r for r in board}
    bets={i:read_csv(STATE_OUT/'bets'/f'{i}.csv') for i,_ in RULES}
    base={r['id']:r for r in bets['C00']};quality={}
    for ident,rows in bets.items():
        mae=np.mean([abs(float(r['rawPrediction'])-float(r['actualHomeMargin'])) for r in rows])
        winner=sum(float(r['rawPrediction'])*float(r['actualHomeMargin'])>0 for r in rows)
        common=[r for r in rows if r['modelResult']!='PASS' and base[r['id']]['modelResult']!='PASS']
        flipped=[r for r in common if (float(r['prediction'])-float(r['marketHomeMargin']))*(float(base[r['id']]['prediction'])-float(r['marketHomeMargin']))<0]
        selectedwins=sum(r['modelResult']=='W' for r in flipped);baselineswins=sum(base[r['id']]['modelResult']=='W' for r in flipped)
        quality[ident]={'MAE':float(mae),'winnerCorrect':winner,'games':len(rows),
                        'changedSidesOnCommonBets':len(flipped),'variantWinsOnFlips':selectedwins,'baselineWinsOnFlips':baselineswins}
    targets_rows=read_csv(STATE_OUT/'game-targets.csv')
    audits={}
    for y in (2023,2024,2025):
        rows=[r for r in targets_rows if int(r['season'])==y]
        audits[y]={'allCompletedGames':len(rows),'validQuarterGames':sum(truth(r['quarterDataValid']) for r in rows),
                   'validOvertimeGames':sum(truth(r['overtime']) for r in rows),
                   'FBSOvertimeGames':sum(truth(r['fbs']) and truth(r['overtime']) for r in rows),
                   'primaryTargetOpposesWinner':sum(float(r['STATE_SOFT'])*float(r['finalMargin'])<0 for r in rows)}
    (STATE_OUT/'diagnostics.json').write_text(json.dumps({'predictionMetrics':quality,'inputChecks':audits},indent=2)+'\n')
    primary=stats['STATE_SOFT'];baseline=stats['C00'];q=quality['STATE_SOFT']
    lines=['# Game-state and overtime backtest (local only)','',
           f"Prespecified primary model: **{primary['wins']}-{primary['losses']} ({pct(primary['winRate'])}), {money(primary['profit'])}, {pct(primary['ROI'])} ROI**. Baseline: {baseline['wins']}-{baseline['losses']}, {money(baseline['profit'])}. Difference: {money(primary['profit']-baseline['profit'])}.",'',
           'All settings were saved in `plan.json` before evaluation. No subsequent parameter optimization. The same 1,858 bookmaker-line matches and 47 weekly forecast periods were used for all six variants. All work is local; no production changes, commits or pushes.','',
           '## All variants','', '| Model | W-L | Passes | Win rate | Profit | ROI | Margin MAE |','|---|---:|---:|---:|---:|---:|---:|']
    for ident,_ in RULES:
        r=stats[ident];lines.append(f"| {LABELS[ident]} | {r['wins']}-{r['losses']} | {r['passes']} | {pct(r['winRate'])} | {money(r['profit'])} | {pct(r['ROI'])} | {quality[ident]['MAE']:.3f} |")
    lines+=['','## By season','', '| Model | 2023 profit | 2024 profit | 2025 profit (through W14) |','|---|---:|---:|---:|']
    for ident,_ in RULES:
        r=stats[ident];lines.append(f"| {LABELS[ident]} | {money(r['profit2023'])} | {money(r['profit2024'])} | {money(r['profit2025'])} |")
    lines+=['','## What changed','',
            '- Primary quarter weights: first quarter 1.0; later quarters use the actual score entering that quarter, never the final score. Full weight when the lead is at most 28 entering Q2, 21 entering Q3, or 14 entering Q4. Beyond that, `weight = 1 / (1 + ((abs(lead)-threshold)/14)^2)`. Example: a 28-point lead entering Q4 gives that quarter half weight; a 42-point lead gives one-fifth weight.',
            '- Both teams\' scoring in that quarter gets the same weight. A comeback restores weight at the next quarter boundary once the actual lead shrinks. The early deficit still counts; no quarter is retrospectively discarded.',
            '- Sum the weighted quarter margins. The primary soft cap retains the first 28 points fully, plus 25% of any additional margin. Add 2.75 for the actual winner (subtract for the loser). The hard-cap control stops at 28 instead. The soft-cap-only control uses the unweighted regulation margin.',
            '- Valid overtime games are regulation ties with extra periods. The modified models assign only the 2.75 win bonus, regardless of the overtime scoring margin. Quarter-weighted artificial advantages are also discarded when regulation ends tied.',
            '- The production baseline keeps its original halftime rule and overtime handling. The overtime-only control keeps that halftime rule for non-OT games. Other models replace the halftime rule, not layer the new quarter weights on top of it.',
            '- Missing, inconsistent, or malformed quarter scores fall back to the original capped-final target. No external Elo, win probability, excitement index, play-by-play, or inferred substitutions are used.',
            '', '## Betting and temporal safeguards','',
            '- $110 risk per bet, +$100 win; no bet before Week 4. Same explicit closing lines, half-point prediction rounding, zero-edge passes, and +3 home advantage (0 at neutral sites).',
            '- Prior weights: W4=1, W5=.75, W6=.5, W7=.25, W8+=0; postseason 0. Fixed pre-2023 bootstrap; 2024/2025 priors regenerated from the preceding season with each variant\'s own rule.',
            '- Fit each forecast period on the exact previously audited game IDs, all kicked off more than 12 hours before its first kickoff. No future-period result is in a training fit. Batched least squares solves distinct target columns, with baseline predictions checked against the earlier backtest to within 1e-7 and every result matched exactly.',
            '- These seasons have already informed our hypotheses, so this is exploratory retrospective testing, not independent validation. Historical lines lack independent capture timestamps; flat -110 is hypothetical because actual prices varied. 2025 FBS results end in Week 14.',
            '', '## Additional checks','',
            f"On games both models bet, the primary changes sides on {q['changedSidesOnCommonBets']} games: it wins {q['variantWinsOnFlips']} of those versus the baseline's {q['baselineWinsOnFlips']}. This isolates actual side changes from differences in no-edge passes.",
            '', f"Using unrounded predictions to bet every matched game, the primary earns {money(primary['rawProfit'])} ({pct(primary['rawWinRate'])} win rate; {pct(primary['rawROI'])} ROI).",
            '', 'A limitation of this weighting rule: a winner can retain a negative adjusted performance target if it spent much of the game far behind and its comeback points were discounted. That follows the symmetric score-state rule; it is not overridden to flatter the winner. Quarter scores cannot identify a competitive comeback occurring within a quarter, defensive scores, substitutions, or possessions. Counts are in `diagnostics.json`.',
            '', '## Files','',
            '- `leaderboard.csv/json`: complete results for all variants.',
            '- `bets/`: every prediction, pick and outcome.',
            '- `weekly-ratings/`: all weekly model outputs.',
            '- `game-targets.csv`: each historical game\'s transformed margin under every rule.',
            '- `diagnostics.json`: quarter/OT coverage, margin errors and common-bet side changes.',
            '- `plan.json`: prespecified formulas, settings and source hashes.',
            '', 'Reproduce with `python game_state_backtest.py`, `python -m unittest test_game_state test_backtest test_grid_search -v`, and `python game_state_report.py`.']
    (STATE_OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,ax=plt.subplots(figsize=(10,5.5))
    ids=[i for i,_ in RULES];profits=[stats[i]['profit'] for i in ids]
    ax.barh([LABELS[i] for i in ids],profits,color=['#607e96' if i!='STATE_SOFT' else '#b47d37' for i in ids])
    ax.axvline(0,color='#333',lw=1);ax.invert_yaxis()
    for index,value in enumerate(profits):ax.text(value-150,index,money(value),ha='right',va='center',fontsize=10)
    ax.set_xlim(min(profits)-1900,max(0,max(profits))+700)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'${x:,.0f}'))
    ax.set_xlabel('Profit at $110 risk per bet; wins earn $100')
    ax.set_title('Game-state backtest: 2023-2025 pooled',pad=15,fontsize=15)
    ax.spines[['top','right']].set_visible(False)
    fig.text(.5,.015,'Same 1,858 line matches | 2025 through Week 14 | Prespecified primary and controls; exploratory historical results',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(STATE_OUT/'comparison.png',dpi=170)
    print(json.dumps({'primary':primary,'predictionMetrics':quality,'inputChecks':audits},indent=2))

if __name__=='__main__':main()
