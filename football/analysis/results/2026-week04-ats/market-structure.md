# Does Prove It differ meaningfully from the market?

Exploratory analysis of 62 supplied confirmed closing lines. Uses frozen Week 4 pregame predictions, not refitted Week 5 ratings. Continuous analyses use stored unrounded margins; the primary presentation adds the subsequently chosen three-point home advantage. The original zero-adjustment version and the 50 FBS-vs-FBS games are also reported in market-structure.json. No neutral games occur in this sample. Nothing here changes the model or picks.

## Hypothesis 1: essentially the same lines, with tiny random deviations

Home-adjusted correlation with market lines is 0.954 overall, or 0.928 within FBS-vs-FBS. Both usually agree on the winner (58/62 and 46/50). But average absolute disagreement is 4.53 points overall and 4.15 FBS-only; 14/62 differences exceed or equal seven points. That is materially different from merely rounding the market. Correlation alone mostly measures agreement about which teams are stronger, not an ATS advantage.

## Hypothesis 2: differences reflect systematic compression

For FBS-vs-FBS games, the descriptive fitted relationship is approximately model home margin = -0.41 + 0.879 * market home margin. The bootstrap 95% interval on the slope is 0.792 to 0.978. This is consistent with deliberate compression rather than deviations centered identically around every market line. Among twelve FBS-vs-FBS games with market spreads of at least 14, the average market favorite margin was 23.42; the model gave those same favorites 20.24. On lines below seven, the average shortfall was only 0.57.

However, a simple structural model (home offset, market margin, and FCS-matchup indicator signed toward the market favorite) explains only 15.0% of the variation in all-game disagreements, dropping to 5.5% under leave-one-game-out prediction. For FBS-only, the figures are 10.5% and 3.5%. It is not just one simple rescaling of Vegas. The remaining differences have a standard deviation around five points; unexplained does not automatically mean informative.

## Hypothesis 3: the distinctive disagreements identify market mistakes

The correlation between model-minus-market and actual-minus-market is 0.009 overall, and -0.102 within FBS-vs-FBS. Thus larger directional disagreements did not consistently anticipate directional market errors this week.

Controlling for market margin, home offset and the FCS indicator, the coefficient on the remaining model disagreement is +0.12 points of realized market error per model point, with a 10,000-resample bootstrap interval of -0.61 to +0.91. FBS-only: -0.11, interval -1.03 to +0.83. Both are compatible with zero as well as potentially useful signal; the data are too limited to distinguish these possibilities.

## Hypothesis 4: the same broad underdog policy could achieve this record randomly

Shuffle the model's rounded favorite/underdog/no-pick choices among games within four strata: FBS-vs-FBS lines under 7, 7 to under 14, and 14+, plus FBS-vs-FCS (all 14+ here). This preserves the exact number of favorite selections, underdog selections and no-picks in each stratum. Grade each shuffled slate against the observed results. This is a conditional random-assignment benchmark, not a claim about how the original picks were generated.

Across 10,000 shuffles, the mean was 30.43 wins, with a 95% simulated range of 24 to 37. The actual 31 wins are near the center; 48.6% of shuffled slates did at least as well. FBS-only: actual 23 wins, versus 24.54 on average under shuffling. So this week's game-specific choices did not outperform an equally underdog-inclined randomized policy.

## Interpretation and limits

The model has an identifiable compression tendency plus substantial game-specific departures from the market. This week does not establish that those departures carry information the market misses. Comparable ATS records do not establish a separate optimum or equally good ordering. The analyses were selected after seeing the week's broad results, the home adjustment was examined retrospectively, bootstrap resampling assumes independent games, and teams are linked through schedules. These are exploratory descriptive checks, not a validated betting strategy or proof of no signal.

Track the same metrics prospectively over future weeks: signed disagreement versus market error, the conditional shuffle benchmark, compression by market spread, and FBS-vs-FBS versus FBS-vs-FCS. Save predictions before kickoff. A claim of improving in the second half of the season needs future or historical held-out weeks, not more tuning on these 62 games.

Reproduce with `python analysis/ats_week04.py` then `python analysis/market_structure.py` from football/. `market-comparison.png` illustrates market agreement and the absence of an obvious directional advantage this week. All numerical analysis uses only user-supplied data; workbook closing-line labels were not independently verified.
