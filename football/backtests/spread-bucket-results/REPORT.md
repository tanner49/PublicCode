# Production model: bookmaker spread buckets

Same frozen production halftime1.25 model; no refits or optimization. Absolute bookmaker handicap, not the model prediction or model-market edge. Boundaries are lower-inclusive, upper-exclusive; exactly 5 belongs to 5-<10; exactly 25 belongs to 25+.

2023-2025 combined; 2025 through Week 14. Same explicit-close sample, Week 4 onward, +3 home (neutral 0), decaying prior, hypothetical -110 pricing, $110 risk/$100 win. Exact no-edge predictions are passed. All work remains local.

| Absolute spread | W-L | Passes | Win rate | Profit | ROI | 95% win-rate interval |
|---|---:|---:|---:|---:|---:|---|
| 0-<5 | 304-308 | 26 | 49.67% | $-3,480 | -5.17% | 45.7%-53.6% |
| 5-<10 | 248-237 | 16 | 51.13% | $-1,270 | -2.38% | 46.7%-55.6% |
| 10-<15 | 156-145 | 7 | 51.83% | $-350 | -1.06% | 46.2%-57.4% |
| 15-<20 | 78-83 | 6 | 48.45% | $-1,330 | -7.51% | 40.9%-56.1% |
| 20-<25 | 60-55 | 4 | 52.17% | $-50 | -0.40% | 43.1%-61.1% |
| 25+ | 65-56 | 4 | 53.72% | $+340 | +2.55% | 44.9%-62.4% |

## Profit by year

| Absolute spread | 2023 | 2024 | 2025 through W14 |
|---|---:|---:|---:|
| 0-<5 | $-860 (50.3%) | $-1,220 (49.8%) | $-1,400 (49.0%) |
| 5-<10 | $-2,640 (44.0%) | $-1,660 (47.6%) | $+3,030 (60.8%) |
| 10-<15 | $-670 (48.9%) | $+340 (54.0%) | $-20 (52.3%) |
| 15-<20 | $-460 (48.0%) | $-610 (47.5%) | $-260 (50.0%) |
| 20-<25 | $+330 (56.4%) | $-730 (43.9%) | $+350 (57.1%) |
| 25+ | $-50 (51.6%) | $+630 (59.5%) | $-240 (50.0%) |

## Interpretation safeguards

- Six buckets are exploratory subgroup checks of already-inspected seasons. A profitable bucket alone does not establish a repeatable strategy.
- The JSON/CSV includes one-sided binomial tail probabilities against the -110 break-even rate (52.38%), and a six-comparison Bonferroni correction. These are only iid benchmarks; shared teams and weeks create dependence. They do not correct for every earlier analysis we have tried.
- `unrounded-sensitivity.csv` uses unrounded predictions, avoiding pass changes from display rounding. `favorite-underdog.csv` separates picks by side as a descriptive check, not a separately optimized strategy.
- Line provenance and coverage limitations from the original backtest still apply; missing/malformed lines are excluded consistently.

Source SHA-256: `8a0cb393458d67d45feb31d580734e4aa0842f4e3f433b6584d99d60c840bf62`. Reproduce with `python spread_buckets.py`.
