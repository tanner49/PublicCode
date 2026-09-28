# Private parameter search: 25 broad candidates + 10 refinements

Best tested candidate: **R09**, 903-860 (51.22%), **-$4,300**, -2.22% ROI. Baseline: -$6,140, 50.75%.

**All three years were used to choose the parameters. These are optimized in-sample results, not an independently validated edge.** No deployment, commit, or push was performed.

## Selected settings

| Parameter | Baseline | Best tested |
|---|---:|---:|
| Winner bonus | 2.75 | 0 |
| Final-margin cap | 28 | 28 |
| Halftime multiplier | 1.25 | 1 |
| Prior decay (start, step) | (4, .25) | (4, 0.1875) |

The prior weight for forecast week W is `max(0, 1 - max(0, W-start)*step)`. Start means the last week at full weight; the first decrement is the following week. Postseason weight stays zero.

| Forecast week | Baseline prior | Best prior |
|---|---:|---:|
| 4 | 1 | 1 |
| 5 | 0.75 | 0.8125 |
| 6 | 0.5 | 0.625 |
| 7 | 0.25 | 0.4375 |
| 8 | 0 | 0.25 |
| 9 | 0 | 0.0625 |
| 10 | 0 | 0 |
| 11 | 0 | 0 |
| 12 | 0 | 0 |
| 13 | 0 | 0 |

## Year-by-year results

| Season | Baseline profit | Best W-L | Best win rate | Best profit | Best ROI |
|---|---:|---:|---:|---:|---:|
| 2023 | -$4,350 | 269-270 | 49.91% | -$2,800 | -4.72% |
| 2024 | -$3,250 | 324-308 | 51.27% | -$1,480 | -2.13% |
| 2025 (through Week 14) | +$1,460 | 310-282 | 52.36% | -$20 | -0.03% |

The winning candidate risked $193,930 over 1763 bets and passed 95 exact no-edge games. Unrounded predictions, betting every matched game, returned -$5,930 (50.86%; ROI -2.90%).

0/35 candidates were profitable overall; 0/35 were profitable in every season. The best coarse candidate was C01 at -$4,740; refinement changed the best profit by +$440.

## Top ten tested candidates

| ID | Bonus | Cap | Half multiplier | Decay start / step | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| R09 | 0 | 28 | 1 | 4 / 0.1875 | 903-860 | 51.22% | -$4,300 | -2.22% |
| R04 | 0 | 31.5 | 1 | 4 / 0.25 | 913-871 | 51.18% | -$4,510 | -2.30% |
| R10 | 0 | 28 | 1 | 4 / 0.3125 | 901-862 | 51.11% | -$4,720 | -2.43% |
| C01 | 0 | 28 | 1 | 4 / 0.25 | 903-864 | 51.10% | -$4,740 | -2.44% |
| R08 | 0 | 28 | 1 | 5 / 0.25 | 901-863 | 51.08% | -$4,830 | -2.49% |
| R01 | 0.75 | 28 | 1 | 4 / 0.25 | 907-870 | 51.04% | -$5,000 | -2.56% |
| R07 | 0 | 28 | 1 | 3 / 0.25 | 902-866 | 51.02% | -$5,060 | -2.60% |
| C10 | 2.75 | 21 | 1.25 | 4 / 0.25 | 906-870 | 51.01% | -$5,100 | -2.61% |
| C08 | 1.5 | 42 | 2 | 4 / 0.25 | 926-889 | 51.02% | -$5,190 | -2.60% |
| C03 | 0 | 42 | 1.5 | 3 / 0.25 | 919-883 | 51.00% | -$5,230 | -2.64% |

## Method and limits

- Sparse factorial design: 24 points from a five-level orthogonal array, plus the production baseline. This is a broad 25-model sample, not an exhaustive Cartesian product. Bonus levels: 0, 1.5, 2.75, 4, 6. Cap levels: 21, 28, 35, 42, 56. Halftime levels: 0, 1, 1.25, 1.5, 2. Prior schedules: (3,.5), (3,.25), (4,.25), (5,.25), (5,.125). A zero multiplier removes the halftime adjustment.
- Ten refinements around the coarse winner: each numerical coordinate one step down and up. Steps: bonus .75; cap 3.5; multiplier .125; decay start 1 week; decay rate .0625. At a bound, use distinct inward neighbors. Refinement settings were saved before evaluating them. A limited search finds the best tested setting, not a proven global or local maximum.
- Objective fixed before evaluation: pooled dollar profit at $110 risk / $100 win; ties broken by ROI, then worst-year profit. No model changes based on individual game results.
- Same 1,858 ESPN-labeled closing-line games, 47 chronological forecast periods, +3 home advantage, neutral-site 0, half-point prediction rounding, and exact no-edge passes. Same guarded halftime rule: winner led by at least 21 at half and won by at least 10; half-credit ceiling 56. Those guardrails were not tuned.
- 2023 uses the same frozen 2022 bootstrap for every candidate. For 2024/2025, regenerate the prior from the preceding season using that candidate's parameters. Winner bonus also changes the inherited prior encoding. Prior values within 1e-9 of zero are snapped to zero to avoid a floating-point sign triggering a spurious bonus.
- Ratings were fit before each period with the original audited training IDs and 12-hour completion buffer. Candidates sharing the same prior weight are solved together with separate target vectors; this is numerically equivalent to separate least-squares fits. The baseline is asserted to reproduce every prior prediction within 1e-7 and every ATS result exactly.
- Model selection uses outcomes from all three years, so the selected configuration has selection bias despite temporally clean ratings. The apparent win rate is optimistically selected. 2025 also informed earlier model development. A new future sample is needed to test the selected model.
- Historical-line limitations from the original report remain: API-labeled closes lack independent capture timestamps; actual juice varied, while this experiment assumes -110 universally. 2025 supplied FBS results stop at Week 14. No odds-source changes or extra filters were selected to improve results.

## Saved locally

- `grid-results/leaderboard.csv` and `.json`: all 35 configurations, per-year results and unrounded sensitivity.
- `grid-results/search-plan.json`, `refinement-plan.json`: design, objective, settings and input hashes.
- `grid-results/bets/`: a complete game ledger for every candidate.
- `grid-results/weekly-ratings/`: compressed NumPy archives containing team names, candidate IDs, ratings and prior weights for every period.
- `results/weekly-audit.json`: shared exact training IDs and cutoffs.
- `grid_search.py`, `test_grid_search.py`, `grid_report.py`: reproducible implementation, checks and report generation.

Run `python grid_search.py`, `python -m unittest test_grid_search -v`, then `python grid_report.py`. Everything stays in this private local folder.
