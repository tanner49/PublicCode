# 2026 home adjustment experiment

Subtract 3 from each non-neutral home-team game target AFTER the existing capped/halftime-adjusted margin and 2.75 winner bonus. Keep prior targets and all row weights unchanged. Predictions still add 3 at home, zero at neutral sites.

Weeks 4-6 train on their own archived pre-week CSVs, never later corrected exports. Evaluation game IDs are excluded and training kickoff dates precede the first evaluated fixture. Baseline half-point forecasts exactly match the existing saved forecasts. Prior weights: Week 4 retrospective halftime comparison 0.75, Week 5 0.75, Week 6 0.5. This does not test zero-prior behavior specifically. Week 4 was previously used in model development. Week 5 uses saved lines including retrospective Thursday closes; Week 6 uses the October 10 close/current capture, not uniformly pregame-locked lines.

179 games. Baseline: 90-84-1, 4 passes. Adjusted: 92-80-1, 6 passes. Raw-margin MAE 12.850 -> 12.687; RMSE 16.146 -> 16.018. Small retrospective improvement, not independent evidence of a persistent edge. No production model or website changes.

Reproduce: python analysis/home_adjustment_2026.py from football/ or invoke by its full path. Output games.json, summary.json and audit.json retain comparisons and source hashes.
