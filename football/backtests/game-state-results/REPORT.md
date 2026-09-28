# Game-state and overtime backtest (local only)

Prespecified primary model: **906-870 (51.01%), -$5,100, -2.61% ROI**. Baseline: 911-884, -$6,140. Difference: +$1,040.

All settings were saved in `plan.json` before evaluation. No subsequent parameter optimization. The same 1,858 bookmaker-line matches and 47 weekly forecast periods were used for all six variants. All work is local; no production changes, commits or pushes.

## All variants

| Model | W-L | Passes | Win rate | Profit | ROI | Margin MAE |
|---|---:|---:|---:|---:|---:|---:|
| Current halftime model | 911-884 | 63 | 50.75% | -$6,140 | -3.11% | 12.808 |
| Current model + OT treatment | 915-881 | 62 | 50.95% | -$5,410 | -2.74% | 12.795 |
| Cap28 + OT treatment | 900-877 | 81 | 50.65% | -$6,470 | -3.31% | 12.639 |
| Soft cap + OT treatment | 910-869 | 79 | 51.15% | -$4,590 | -2.35% | 12.630 |
| Game-state + hard cap + OT | 905-877 | 76 | 50.79% | -$5,970 | -3.05% | 12.658 |
| Game-state + soft cap + OT (primary) | 906-870 | 82 | 51.01% | -$5,100 | -2.61% | 12.657 |

## By season

| Model | 2023 profit | 2024 profit | 2025 profit (through W14) |
|---|---:|---:|---:|
| Current halftime model | -$4,350 | -$3,250 | +$1,460 |
| Current model + OT treatment | -$4,110 | -$2,440 | +$1,140 |
| Cap28 + OT treatment | -$3,640 | -$1,300 | -$1,530 |
| Soft cap + OT treatment | -$3,440 | -$750 | -$400 |
| Game-state + hard cap + OT | -$3,350 | -$2,110 | -$510 |
| Game-state + soft cap + OT (primary) | -$3,320 | -$2,020 | +$240 |

## What changed

- Primary quarter weights: first quarter 1.0; later quarters use the actual score entering that quarter, never the final score. Full weight when the lead is at most 28 entering Q2, 21 entering Q3, or 14 entering Q4. Beyond that, `weight = 1 / (1 + ((abs(lead)-threshold)/14)^2)`. Example: a 28-point lead entering Q4 gives that quarter half weight; a 42-point lead gives one-fifth weight.
- Both teams' scoring in that quarter gets the same weight. A comeback restores weight at the next quarter boundary once the actual lead shrinks. The early deficit still counts; no quarter is retrospectively discarded.
- Sum the weighted quarter margins. The primary soft cap retains the first 28 points fully, plus 25% of any additional margin. Add 2.75 for the actual winner (subtract for the loser). The hard-cap control stops at 28 instead. The soft-cap-only control uses the unweighted regulation margin.
- Valid overtime games are regulation ties with extra periods. The modified models assign only the 2.75 win bonus, regardless of the overtime scoring margin. Quarter-weighted artificial advantages are also discarded when regulation ends tied.
- The production baseline keeps its original halftime rule and overtime handling. The overtime-only control keeps that halftime rule for non-OT games. Other models replace the halftime rule, not layer the new quarter weights on top of it.
- Missing, inconsistent, or malformed quarter scores fall back to the original capped-final target. No external Elo, win probability, excitement index, play-by-play, or inferred substitutions are used.

## Betting and temporal safeguards

- $110 risk per bet, +$100 win; no bet before Week 4. Same explicit closing lines, half-point prediction rounding, zero-edge passes, and +3 home advantage (0 at neutral sites).
- Prior weights: W4=1, W5=.75, W6=.5, W7=.25, W8+=0; postseason 0. Fixed pre-2023 bootstrap; 2024/2025 priors regenerated from the preceding season with each variant's own rule.
- Fit each forecast period on the exact previously audited game IDs, all kicked off more than 12 hours before its first kickoff. No future-period result is in a training fit. Batched least squares solves distinct target columns, with baseline predictions checked against the earlier backtest to within 1e-7 and every result matched exactly.
- These seasons have already informed our hypotheses, so this is exploratory retrospective testing, not independent validation. Historical lines lack independent capture timestamps; flat -110 is hypothetical because actual prices varied. 2025 FBS results end in Week 14.

## Additional checks

On games both models bet, the primary changes sides on 177 games: it wins 86 of those versus the baseline's 91. This isolates actual side changes from differences in no-edge passes.

Using unrounded predictions to bet every matched game, the primary earns -$5,930 (50.86% win rate; -2.90% ROI).

A limitation of this weighting rule: a winner can retain a negative adjusted performance target if it spent much of the game far behind and its comeback points were discounted. That follows the symmetric score-state rule; it is not overridden to flatter the winner. Quarter scores cannot identify a competitive comeback occurring within a quarter, defensive scores, substitutions, or possessions. Counts are in `diagnostics.json`.

## Files

- `leaderboard.csv/json`: complete results for all variants.
- `bets/`: every prediction, pick and outcome.
- `weekly-ratings/`: all weekly model outputs.
- `game-targets.csv`: each historical game's transformed margin under every rule.
- `diagnostics.json`: quarter/OT coverage, margin errors and common-bet side changes.
- `plan.json`: prespecified formulas, settings and source hashes.

Reproduce with `python game_state_backtest.py`, `python -m unittest test_game_state test_backtest test_grid_search -v`, and `python game_state_report.py`.
