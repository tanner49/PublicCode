"""Produce a local report and chart from frozen predictions; never tune the model."""
from backtest import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
plt.rcParams['text.parse_math'] = False

def pct(x):
    return f'{100*x:.2f}%'

def money(x):
    return ('-' if x<0 else '+')+f'${abs(x):,}'

def main():
    report=json.loads((OUT/'summary.json').read_text())
    allrows=read_csv(OUT/'game-by-game.csv')
    rows=[r for r in allrows if r['lineStatus']=='explicit_close' and r['modelAvailable']=='True']
    cross={r['id']:r for r in read_csv(DATA/'crosscheck-training_data.csv') if r['spread']}
    comparisons=[]
    for r in allrows:
        if r['id'] not in cross or r['modelAvailable']!='True':
            continue
        other=cross[r['id']]
        assert other['home_team']==r['home'] and other['away_team']==r['away']
        assert float(other['home_points'])==float(r['homeScore']) and float(other['away_points'])==float(r['awayScore'])
        line=float(other['spread'])
        diff=float(r['homeSpread'])-line if r.get('homeSpread') else None
        comparisons.append({'season':r['season'],'id':r['id'],'home':r['home'],'away':r['away'],
                            'ESPNStatus':r['lineStatus'],'ESPNHomeSpread':r.get('homeSpread'),
                            'crosscheckHomeSpread':line,'difference':diff,
                            'halftime1.25Result':grade(float(r['halftime1.25Prediction']),-line,float(r['actualHomeMargin']))})
    write_csv(OUT/'line-crosscheck.csv',comparisons)
    matched=[r for r in comparisons if r['ESPNStatus']=='explicit_close']
    corroboration={'matchedExplicitClose':len(matched),
                   'withinHalfPoint':sum(abs(r['difference'])<=.5 for r in matched),
                   'withinOnePoint':sum(abs(r['difference'])<=1 for r in matched),
                   'largeDisagreements':[r for r in matched if abs(r['difference'])>4],
                   'crosscheckOnly':{y:summary([r for r in comparisons if r['season']==y]) for y in ['2023','2024']}}
    (OUT/'crosscheck-summary.json').write_text(json.dumps(corroboration,indent=2)+'\n')
    # Descriptive, pre-existing questions: division and later-season performance.
    extra={}
    selections={
        'Weeks 4-7':[r for r in rows if r['period'] in [f'regular-{w:02}' for w in range(4,8)]],
        'Weeks 8+ regular season':[r for r in rows if r['period'].startswith('regular') and int(r['period'].split('-')[1])>=8],
        'Weeks 11+ regular season':[r for r in rows if r['period'].startswith('regular') and int(r['period'].split('-')[1])>=11]}
    for label,rs in selections.items():
        extra[label]=summary(rs)
    (OUT/'descriptive-splits.json').write_text(json.dumps(extra,indent=2)+'\n')
    source_quality={}
    for y in [2023,2024,2025]:
        gs=load_games(y);fg=[g for g in gs if fbs(g)]
        source_quality[y]={'completedGames':len(gs),'validHalves':sum(halftime_margin(g)!=None for g in gs),
                           'FBSGames':len(fg),'validFBSHalves':sum(halftime_margin(g)!=None for g in fg),
                           'lastFBSGame':max(g['StartDate'] for g in fg)}
    (OUT/'score-quality.json').write_text(json.dumps(source_quality,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,5),gridspec_kw={'width_ratios':[1.6,1]})
    colors={2023:'#b85442',2024:'#ad842b',2025:'#27735b'}
    for year,color in colors.items():
        selected=[r for r in rows if int(r['season'])==year and r['halftime1.25Result']!='PASS']
        gains=[0];total=0
        for r in selected:
            total+=int(r['halftime1.25Profit']);gains.append(total)
        axes[0].plot(range(len(gains)),gains,label=str(year)+(' (through W14)' if year==2025 else ''),color=color,lw=2)
    axes[0].axhline(0,color='#888',lw=.8)
    axes[0].yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'${v:,.0f}'))
    axes[0].set(xlabel='Bets placed, starting in Week 4',ylabel='Cumulative profit',title='$110 risked per bet; $100 profit per win')
    axes[0].legend(frameon=False)
    labels=['2023','2024','2025','All']
    stats=[report['samples']['explicitClose'][s]['halftime1.25'] for s in ['2023','2024','2025','all']]
    rates=[100*s['winRate'] for s in stats]
    for i,(rate,s,color) in enumerate(zip(rates,stats,[*colors.values(),'#354f64'])):
        low,high=[100*v for v in s['winRateWilson95']]
        axes[1].errorbar(i,rate,yerr=[[rate-low],[high-rate]],fmt='o',color=color,capsize=5,markersize=8)
    axes[1].set_xticks(range(4),labels)
    axes[1].axhline(100*110/210,color='#333',linestyle='--',label='Break-even: 52.38%')
    for i,rate in enumerate(rates):
        axes[1].annotate(f'{rate:.2f}%',(i,rate),xytext=(9,0),textcoords='offset points',va='center',fontsize=9)
    axes[1].set(ylim=(43,59),xlim=(-.5,3.9),ylabel='Win rate (%) with approximate 95% interval',title='ESPN-labeled closing lines')
    axes[1].legend(frameon=False,loc='upper left')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Prove It: 2023-2025 walk-forward ATS backtest',fontsize=16,weight='bold')
    fig.text(.02,.015,'Halftime 1.25 model | +3 home, neutral 0 | prior fades from W4=1 to W8=0 | historical simulation, not live results',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.94))
    fig.savefig(OUT/'profitability.png',dpi=180)
    lines=['# Private Prove It backtest: 2023-2025','',
           '**The broad test does not reproduce a profitable 57% edge.** Using the production halftime model, ESPN-labeled closing handicaps, and hypothetical -110 prices, the result is 911-884 (50.75%), losing $6,140 on $197,450 risked (-3.11% ROI). No code, data, or results from this analysis were pushed or committed.','',
           '![Profitability](results/profitability.png)','',
           '## Main result','',
           '| Season | W-L | Win rate | Profit | ROI | No-edge passes |',
           '|---|---:|---:|---:|---:|---:|']
    for key,label in [('2023','2023'),('2024','2024'),('2025','2025 through Week 14'),('all','Total')]:
        s=report['samples']['explicitClose'][key]['halftime1.25']
        lines.append(f"| {label} | {s['wins']}-{s['losses']} | {pct(s['winRate'])} | {money(s['profit'])} | {pct(s['ROI'])} | {s['passes']} |")
    lines += ['', 'There were 1,858 eligible model/closing-line matches out of 1,963 supplied completed FBS-involving games from Week 4 onward (94.7%). Of these, 63 had no edge at the displayed half-point precision and were passed. No pushes occurred in this particular line sample; the grading code handles pushes and refunds the stake. Maximum chronological drawdown across the main sample was $9,820.','',
              'The implied break-even rate at -110 is 110/210 = 52.38%. The approximate per-bet Wilson 95% interval is 48.44%-53.06%; games involving shared teams are not fully independent, so this is descriptive, not a definitive confidence guarantee. These results do not establish a betting edge.','',
              '## Exact rules','',
              '- Fresh ratings were fitted for all 47 betting periods. Regular weeks use the earliest kickoff among all supplied games in that week, not just the games with betting lines. Postseason games are grouped Monday-Sunday, with a new fit before the first kickoff in each group.',
              '- Training includes only completed supplied games whose kickoff was more than 12 hours before that cutoff; games in the forecast period itself are excluded. This is a conservative completion buffer because the CSV has kickoff timestamps, not final-whistle timestamps. All training IDs, cutoffs, and ratings are saved.',
              '- Bet from regular Week 4 onward; weights W4=1, W5=.75, W6=.5, W7=.25, W8 onward=0. Postseason prior is 0. The model does not use any bookmaker line when fitting ratings.',
              '- Production halftime1.25 rule: cap final-margin credit at 28; when the eventual winner led by at least 21 at halftime and won by at least 10, allow the greater of capped-final credit and 1.25 times its halftime lead, with a maximum credit of 56. Add the production winner bonus of 2.75. Missing or inconsistent quarter scores use the capped-final rule.',
              '- Forecast home margin = home rating minus away rating +3, or +0 at neutral sites. Rating fitting itself remains unchanged. Production display rounds stored two-decimal predictions to the nearest half point. Pick the side on which the model differs from the market; no edge means no bet.',
              '- Each bet risks $110; wins earn $100, losses lose $110, pushes net $0. No confidence threshold, variable staking, parlaying, or optimization after seeing the results.',
              '- 2023 prior: fit our cap28 model without a prior to 2022 results only. The 2022 schedule archive lacks quarters. 2024 and 2025 priors: prior season final halftime1.25 ratings, with zero prior weight. Teams are mapped by numeric ID across seasons. The original cap28 comparison uses identical priors to isolate the game-target change.',
              '- All inputs and the production implementation are frozen locally with SHA-256 hashes. Final historical CSVs can contain later data corrections; historical as-published revisions are unavailable. The chosen model is retrospective, and 2025 was already used in earlier development, so it is not a pristine untouched holdout.','',
              '## Line provenance and limitations','',
              'Primary lines come from the ESPN core odds API, provider 58 (returned as ESPN BET), using the explicit home/away `close.pointSpread.american` pair. Example endpoint: https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/events/401525853/competitions/401525853/odds . Full responses are cached under `data/odds/`. The selection uses a fixed provider, never whichever bookmaker makes the picks look best. Live-odds provider 59 is excluded.',
              '', 'Both team IDs must match the supplied home/away orientation. Five games with mismatched orientation were excluded, including bowls with conflicting home/neutral designations. Values must be finite, antisymmetric, on a half-point increment, and below 100 in magnitude: some 2023 close fields incorrectly contain American prices such as -115 instead of handicaps. They are not treated as valid closing lines.',
              '', 'These are API-labeled closing lines, not independently timestamped pre-kickoff tickets. Almost all are half-point handicaps, which explains the lack of pushes; many carry prices other than -110. The requested flat -110 assumption is therefore a hypothetical repricing, not evidence that every recorded handicap could actually have been bought at -110.',
              '', f"An independent public CFBD-derived archive corroborates {corroboration['withinHalfPoint']}/{len(matched)} overlapping lines within 0.5 points, and {corroboration['withinOnePoint']}/{len(matched)} within 1 point. It describes its `spread` column as a closing spread but does not identify a consistent bookmaker. It is used as a separate sensitivity check, not to pick favorable lines. Source: https://github.com/zachringnight/cfbmodel/blob/main/info_sheet_data.md . Large disagreements are saved for review in `results/crosscheck-summary.json`.",
              '', '| Season | Explicit closing matches | Archived-current fallback | Excluded odds/identity issues |',
              '|---|---:|---:|---:|']
    for y,c in report['coverage'].items():
        lines.append(f"| {y} | {c.get('explicit_close',0)} | {c.get('archived_current',0)} | {sum(v for k,v in c.items() if k not in ['explicit_close','archived_current'])} |")
    lines += ['', '## Robustness checks, without retuning','',
              '| Check | W-L | Win rate | Profit | ROI |','|---|---:|---:|---:|---:|']
    checks=[('Original cap28, identical priors',report['samples']['explicitClose']['all']['cap28']),
            ('Unrounded model picks: every matched game',report['samples']['explicitClose']['all']['halftimeUnrounded']),
            ('Include archived-current fallback lines',report['samples']['includingArchivedCurrent']['all']['halftime1.25']),
            ('Independent archive, 2023 subset',corroboration['crosscheckOnly']['2023']),
            ('Independent archive, 2024 subset',corroboration['crosscheckOnly']['2024'])]
    for label,s in checks:
        lines.append(f"| {label} | {s['wins']}-{s['losses']} | {pct(s['winRate'])} | {money(s['profit'])} | {pct(s['ROI'])} |")
    lines += ['', 'Unrounded picks address the literal bet-every-game interpretation and lead to the same overall conclusion. The independent archive covers a different subset, mainly Week 5 onward; its results are not directly comparable to the full primary seasons. No source was chosen because of its betting return.','',
              '## Descriptive follow-ups','',
              '| Group | W-L | Win rate | Profit | ROI |','|---|---:|---:|---:|---:|']
    splits=[('FBS vs FBS',report['samples']['explicitClose']['FBSvsFBS']['halftime1.25']),
            ('FBS vs lower division',report['samples']['explicitClose']['FBSvsOther']['halftime1.25']),*extra.items()]
    for label,s in splits:
        lines.append(f"| {label} | {s['wins']}-{s['losses']} | {pct(s['winRate'])} | {money(s['profit'])} | {pct(s['ROI'])} |")
    lines += ['', 'FBS/lower-division games and late-season games are plausible areas for a future preregistered test, but these smaller descriptive slices are not validated betting strategies. The overall strategy requested here loses money.','',
              '## Reproduction and audit files','',
              'From this folder: `python backtest.py`, `python -m unittest test_backtest -v`, then `python report.py`. Dependencies: numpy, requests, matplotlib. `fetch_historical_odds.py` downloads only public game-odds responses and reuses the cache; it does not upload model information.',
              '', '- `results/game-by-game.csv`: every eligible fixture, line status, predictions, picks, result and profit.',
              '- `results/weekly-ratings/`: all 47 fresh fits, both model variants.',
              '- `results/weekly-audit.json`: exact training IDs, cutoff, prior weight, and quarter-score coverage.',
              '- `results/prior-2023.csv` through `prior-2026.csv`: reproducible priors; the 2026 output is unused by this test.',
              '- `results/weekly-explicitClose.csv`: weekly outcomes.',
              '- `results/summary.json`: aggregate results, input/code hashes and policy.',
              '- `results/score-quality.json`, `line-crosscheck.csv`, `crosscheck-summary.json`: data-quality evidence.',
              '- `production_ratings.py`: frozen copy of the production code; no production files were changed.',
              '', '2022 bootstrap schedule source: https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/cfb_schedules . Initial betting archive discovery: https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_betting . Schema documentation: https://github.com/sportsdataverse/cfbfastR-cfb-data/blob/main/DATASETS.md . Supplied 2023/2024 exports are copied unchanged; 2025 is the existing `cfbweek15.csv` archive, with completed FBS games only through Week 14. No missing 2025 bowls were fabricated.',
              '', 'Six automated checks passed: grading including pushes; prior schedule; future-score perturbation leaves earlier fits unchanged; every saved temporal cutoff; profit accounting; and halftime credit/fallback behavior.']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(corroboration,indent=2))

if __name__=='__main__':
    main()
