# Production model by betting week

Frozen halftime1.25 production model; same explicit-close sample and $110 stake / $100 win. No bets before Week 4; +3 home (neutral 0); prior fades to zero by Week 8. Betting week is the week being predicted, not the final training week. No model refits or settings changes.

## Pooled weeks

| Week / phase | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---:|
| 4 | 55-55 | 50.00% | $-550 | -4.55% |
| 5 | 88-76 | 53.66% | $+440 | +2.44% |
| 6 | 68-76 | 47.22% | $-1,560 | -9.85% |
| 7 | 77-82 | 48.43% | $-1,320 | -7.55% |
| 8 | 84-88 | 48.84% | $-1,280 | -6.77% |
| 9 | 81-79 | 50.62% | $-590 | -3.35% |
| 10 | 79-81 | 49.38% | $-1,010 | -5.74% |
| 11 | 84-80 | 51.22% | $-400 | -2.22% |
| 12 | 80-82 | 49.38% | $-1,020 | -5.72% |
| 13 | 96-83 | 53.63% | $+470 | +2.39% |
| 14 | 78-57 | 57.78% | $+1,530 | +10.30% |
| 15 | 4-2 | 66.67% | $+180 | +27.27% |
| 16 | 0-1 | 0.00% | $-110 | -100.00% |
| Postseason | 37-42 | 46.84% | $-920 | -10.59% |

## Season phases

| Week / phase | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---:|
| Weeks 4-7 | 288-289 | 49.91% | $-2,990 | -4.71% |
| Weeks 8-10 | 244-248 | 49.59% | $-2,880 | -5.32% |
| Weeks 11-14 | 338-302 | 52.81% | $+580 | +0.82% |
| Weeks 15-16 | 4-3 | 57.14% | $+70 | +9.09% |
| Postseason | 37-42 | 46.84% | $-920 | -10.59% |

## 2023 phases

| Week / phase | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---:|
| Weeks 4-7 | 74-85 | 46.54% | $-1,950 | -11.15% |
| Weeks 8-10 | 77-91 | 45.83% | $-2,310 | -12.50% |
| Weeks 11-14 | 104-87 | 54.45% | $+830 | +3.95% |
| Weeks 15-16 | 0-0 | N/A | $+0 | N/A |
| Postseason | 15-22 | 40.54% | $-920 | -22.60% |

## 2024 phases

| Week / phase | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---:|
| Weeks 4-7 | 104-96 | 52.00% | $-160 | -0.73% |
| Weeks 8-10 | 77-85 | 47.53% | $-1,650 | -9.26% |
| Weeks 11-14 | 107-111 | 49.08% | $-1,510 | -6.30% |
| Weeks 15-16 | 4-3 | 57.14% | $+70 | +9.09% |
| Postseason | 22-20 | 52.38% | $+0 | +0.00% |

## 2025 phases

| Week / phase | W-L | Win rate | Profit | ROI |
|---|---:|---:|---:|---:|
| Weeks 4-7 | 110-108 | 50.46% | $-880 | -3.67% |
| Weeks 8-10 | 90-72 | 55.56% | $+1,080 | +6.06% |
| Weeks 11-14 | 127-104 | 54.98% | $+1,260 | +4.96% |
| Weeks 15-16 | 0-0 | N/A | $+0 | N/A |
| Postseason | 0-0 | N/A | $+0 | N/A |

## Coverage and interpretation

- 2023 Week 4 has zero usable explicit closing lines under the existing quality filter; its malformed/current-only lines remain excluded. Week 4 therefore pools 2024 and 2025 only. `weekly.csv` shows supplied and matched counts by year.
- 2025 supplied completed FBS games end at Week 14. Weeks 15-16 have very few games and differing calendar coverage; postseason is separate. Week numbering follows the supplied season exports.
- Weeks 4-7, 8-10, and 11-14 were chosen before inspecting this breakdown. No best start-week strategy is selected. The previous conversation already examined late-season splits, so these are exploratory summaries, not new holdout evidence.
- Better results late can reflect more data, prior decay, changing opponents/game mix or chance; this table cannot identify the cause. Results share teams and are not independent draws.
- Archived handicap and hypothetical -110 pricing limitations are unchanged. Exact no-edge picks are skipped. Raw-prediction profitability is included as a sensitivity column.

Input SHA-256: `8a0cb393458d67d45feb31d580734e4aa0842f4e3f433b6584d99d60c840bf62`. Reproduce with `python week_analysis.py`. Everything remains local.
