# Prove It football backtests

Research code, frozen inputs, and reproducible results for the scores-only Prove It model. Published with the owner's authorization after the experiments were completed. Older reports retain their original wording about being private/local and not pushed; that describes their status when written, not their current availability.

## Results

- [Original 2023-2025 walk-forward backtest](REPORT.md)
- [25 broad parameter combinations and 10 refinements](grid-results/REPORT.md)
- [ROI distribution across those 35 configurations](grid-results/roi-histogram.png)
- [Quarter game-state weighting and overtime controls](game-state-results/REPORT.md)
- [Bookmaker spread buckets](spread-bucket-results/REPORT.md)
- [Performance by betting week](week-results/REPORT.md)
- [Week 12 onward, absolute bookmaker spread greater than 10](late-large-spread-results/summary.json)

These are **against-the-spread** tests, not over/under total-score predictions. The pooled production backtest returned 911 wins and 884 losses (50.75%), with 63 no-edge passes, losing $6,140 at a hypothetical $110 risk / $100 win. No parameter-search candidate was profitable across all three years. These are exploratory historical results, not a validated betting edge.

## Scope and reproduction

Run commands from this directory. Install dependencies with `python -m pip install -r requirements.txt`.

```text
python -m unittest test_backtest test_grid_search test_game_state -v
python backtest.py
python report.py
python grid_search.py
python grid_report.py
python roi_histogram.py
python game_state_backtest.py
python game_state_report.py
python spread_buckets.py
python week_analysis.py
```

`production_ratings.py` is the frozen implementation used in these experiments. It is imported by the backtests; use the parent football directory's publishing commands for the actual website. The research scripts do not publish the website.

Every betting period is fitted separately using earlier completed games only, with a 12-hour completion buffer. Betting starts in Week 4, with prior weights 1, .75, .5, .25, then 0 from Week 8. Forecasts include +3 home advantage and none at neutral venues. The common sample includes 1,858 usable ESPN-labeled closing handicaps across 2023-2025. Supplied 2025 FBS results stop at Week 14. Full coverage and input hashes are in the reports and manifests.

The parameter search uses all three years for selection; its apparent improvement is in-sample. The later spread/week intersections are exploratory as well. No-edge passes, missing lines, prior generation, and quarter-score fallbacks are recorded rather than silently filled in.

## Data provenance

- `data/games_2023.csv`, `games_2024.csv`, and `games_2025.csv`: supplied CollegeFootballData season exports. Exporter: <https://collegefootballdata.com/exporter/games>.
- `data/cfb_schedules_2022.csv.gz`: SportsDataverse all-division schedule archive used to bootstrap the 2023 prior: <https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/cfb_schedules>.
- `data/odds/`: cached public ESPN core odds responses by season/game. `fetch_historical_odds.py` reproduces downloads. Provider 58's explicit closing handicap is the primary source; malformed fields and identity mismatches are excluded. Actual prices vary; -110 is a hypothetical uniform price.
- `data/betting_*.csv`: SportsDataverse betting archives used during source discovery: <https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/espn_cfb_betting>.
- `data/crosscheck-*`: independent historical line cross-check and its original documentation from <https://github.com/zachringnight/cfbmodel>. The model does not train on those archive features.

Source data remains attributable to its original providers. Saved reports, game ledgers, weekly rating arrays, cutoffs and manifests provide the audit trail. The original experiment's code hashes describe the files at execution time; documentation added for publication does not change the saved predictions.
