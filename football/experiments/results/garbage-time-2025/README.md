# 2025 garbage-time rule backtest

## Finding

No meaningful predictive improvement in this export. For 704 FBS-versus-FBS games in Weeks 2-14, mean absolute error fell by 0.0037 points while correct winner picks fell from 504 to 502. Weeks 4-14 tell the same story. Keep the production model unchanged on this evidence.

## Data and method

- Input: `archive/2025/cfbweek15.csv`, all 3,699 scored regular-season games, Weeks 1-14. Latest kickoff: 2025-11-30 04:00 UTC (November 29 US time). The export does not cover the complete final season or postseason.
- Usable quarter scores: 3,673 of 3,699 games; all 752 FBS-versus-FBS games. Require at least four nonnegative integer period scores per team and totals matching the final score. Missing/inconsistent quarter data falls back to the original margin.
- Candidate rule: a team ahead by at least 28 after Q3 that wins by at least 10 receives at least 28 margin credit. Apply the existing 28-point cap and 2.75 winner bonus afterward. Home and away treated symmetrically.
- Each week from 2 through 14: refit using only earlier weeks, also checking kickoff precedes the first game in the prediction week. Predict every eligible game in the next week. No within-week updating.
- Both models use the current production settings: one-game prior weight 1.0, the archived 2024 priors, original prior transformation/normalization, and no home advantage. No 2025 final ratings are used as priors. No thresholds or parameters were tuned on the evaluation outcomes.
- Week 1 supplies training games. The model rates teams only after their first completed game; 191 later games with an unrated participant are excluded equally from both variants. All 607 FBS-versus-FBS games in Weeks 4-14 were evaluable.
- Evaluate unrounded predicted home-minus-away margins against actual final margins, including overtime. Winner accuracy uses the sign of that prediction; zero does not count as a correct non-tied winner. This is not an against-the-spread test.
- The 95% intervals below resample paired error differences by whole prediction week (10,000 replicates, seed 2025). They are approximate descriptive uncertainty intervals with few weeks and repeated teams, not proof of generalization to another season.

## Results

| Evaluation set | Games | Baseline MAE | Rule MAE | Baseline correct | Rule correct | MAE change |
|---|---:|---:|---:|---:|---:|---:|
| FBS vs FBS, weeks 4-14 | 607 | 12.6811 | 12.6775 | 439 (72.32%) | 437 (71.99%) | -0.0036 |
| FBS vs FBS, weeks 2-14 | 704 | 13.1364 | 13.1327 | 504 (71.59%) | 502 (71.31%) | -0.0037 |
| Any FBS team, weeks 4-14 | 629 | 13.0764 | 13.0824 | 458 (72.81%) | 456 (72.50%) | +0.0061 |
| All divisions, weeks 4-14 | 2878 | 14.0909 | 14.0791 | 2180 (75.75%) | 2181 (75.78%) | -0.0118 |
| All divisions, weeks 2-14 | 3312 | 14.4949 | 14.4844 | 2500 (75.48%) | 2501 (75.51%) | -0.0105 |

Negative MAE change means improvement. Every reported week-bootstrap interval includes zero. For FBS Weeks 2-14 the interval is [-0.0225, +0.0155] points; Weeks 4-14 is [-0.0259, +0.0189].

## How often it matters

The candidate actually changes the capped target for 88 games across all divisions, including 19 FBS-versus-FBS games. Games already won by at least 28 receive exactly the same target in both models. Adjustments from late-season games cannot affect predictions beyond the available export.

Examples:

- Oregon at Northwestern, Week 3: Oregon led by 31 after Q3 and won 34-14. Margin credit rises from 20 to 28.
- Wisconsin at Alabama, Week 3: Alabama led by 28 after Q3 and won 38-14. Credit rises from 24 to 28.
- Purdue at Notre Dame, Week 4: Notre Dame led by 33 after Q3 and won 56-30. Credit rises from 26 to 28.

Four FBS winner picks flip: UTEP vs UL Monroe, Northwestern vs UL Monroe, Wyoming vs Colorado State, and Florida Atlantic vs Tulsa. Three flips hurt and one helps. All four baseline predictions were within 0.52 points of a pick'em.

## Files and reproduction

- `summary.json`: metrics, coverage, and source hashes.
- `predictions.csv`: every paired out-of-sample prediction.
- `adjusted-games.csv`: every game whose capped training target changes.
- `weekly-fbs.csv`: FBS metrics by prediction week.
- `skipped-games.csv`: games excluded because a participant was not yet rated.

From the repository root:

```powershell
python football/experiments/garbage_time_2025.py
```

Production ratings and website data were not modified.
