# Tanner Ratings

Modified Massey college football ratings powering the standalone `/tanner-ratings/` section of `tanner49.github.io`.

## Weekly update

From `PublicCode/football`, install the dependency once:

```powershell
python -m pip install -r requirements.txt
```

Download the season's games from https://collegefootballdata.com/exporter/games (include future fixtures to generate next week's predictions). This link is documented here for the update workflow and is not displayed on the website.

Save each downloaded CSV in `data/raw/2026/` with its publication week. Then run:

```powershell
python ratings.py --input data/raw/2026/week-04.csv --season 2026 --week 4 --rebuild-2025-priors --prior-weight 1 --margin-model cap28
```

For Week 5, save a cumulative export as `week-05.csv` and run:

```powershell
python ratings.py --input data/raw/2026/week-05.csv --season 2026 --week 5 --prior-weight 0.75
```

Week 4 means **completed regular-season games through Week 3**. Future fixtures and missing scores never enter the fit. Completed games with missing scores are excluded and their IDs recorded in the snapshot and printed by the command. The export must contain the full season to date, not just the most recent week. `Completed` accepts true/false or 1/0. Invalid nonempty scores and duplicate completed game IDs stop the build.

The command writes JSON and CSV snapshots locally and copies them to the sibling website repo, updating its snapshot index. Override the website data directory with `--site PATH`. Commit/review both repositories and publish the website through its existing GitHub Pages process. No server, API keys, or additional Jekyll plugins are needed. Published snapshots cannot be silently overwritten with changed data; intentional corrections require archiving/removing the affected JSON in both repos first.

## Method

Ordinary games supply `rating(home) - rating(away) = sign(margin) * (min(abs(margin), 28) + 2.75)`. Ties encode as zero. The production halftime rule described below can increase margin credit beyond 28 when early dominance justifies it; the bonus remains 2.75. The old asymmetric cap is fixed for both current ratings and regenerated 2025 priors.

Equations are weighted by `sqrt(2 / (home games + away games + 2 * prior_weight))`. Prior-season ratings act as pseudo-games against zero, with `prior_weight = 1.0` (the original notebook's approximate one-game setting) and the same signed encoding, capped at 100. Their row weight is `sqrt(2 * prior_weight / (team games + prior_weight))`. This normalization treats the zero-rated baseline as having zero games, so the prior is not exactly equal in influence to any particular real game. A sum-to-zero constraint anchors the least-squares solution. The Week 4 prior weight was 1.0; Week 5 reduces it to 0.75 without changing Week 4. Rebuilding the 2025 prior CSV still uses the archived final notebook's 0.00005 weight on 2024 ratings, so this change does not retroactively alter the 2025 baseline. No home-field adjustment is applied.

All supplied opponents participate in the fit. The site defaults to FBS; division ranks are calculated within each classification and conference filters retain those ranks. Schedule strength is the mean current rating of played opponents. Per the model owner's choice, rating differences are treated as predicted point margins: excess blowout points are assumed to have no additional predictive value. The website displays the favorite minus the absolute margin, rounded to the nearest half-point (halfway values away from zero), with no home-field adjustment. A zero margin is a pick'em. These are model predictions, not sportsbook prices; no moneyline or win probability is inferred.

Early-season ratings can be volatile. Separate schedule networks are only weakly anchored by priors, so cross-division comparisons deserve caution. Teams without completed games have no rating. No earlier 2026 snapshots are fabricated; movement and history begin with Week 4 and appear as future snapshots are added.

## Files

- `backtests/`: [published historical experiments and results](backtests/README.md), including weekly walk-forward tests, parameter search, game-state variants, and spread/week breakdowns. These research scripts are separate from website publishing.

- `ratings.py`: reusable calculation and publishing command.
- `data/raw/2026/week-04.csv`: exact copy of the supplied Desktop download.
- `data/generated/priors-2025.csv`: corrected ratings from the available 2025 export (regular season through Week 16), using the archived 2024 priors. This is the available export, not a claim of a complete final-season dataset.
- `data/generated/2026/`: immutable weekly ratings in JSON and CSV, including input and prior SHA-256 hashes in JSON.
- `archive/2025/`: original football notebooks and CSVs, moved intact, including pre-existing local edits. To run historical notebooks, open them with this folder as the working directory. Their original model remains for reference.

Run verification with `python -m unittest discover -s tests`.

## Prior implementation history

The archived `cbd.ipynb` calls these "Week 0" pseudo-games against a zero-rated baseline and comments `1.0 ~ one game`. Git commit `32c71d8` used weight 2; `c25e1c0` used 0.5; the preserved local notebook used 0.00005. Week 4 used 1.0; Week 5 uses 0.75. Set `--prior-weight` explicitly for each new publication; the CLI default is now 0.75. This is an extra least-squares equation per team, not just an initial solver guess. Its relative influence diminishes as actual games accumulate. The prior target retains the original signed encoding (including the winner bonus), rather than inserting the previous rating completely unchanged.

The superseded local Week 4 snapshot with weight 0.00005 is preserved in `archive/model-revisions/2026-week04-prior-0.00005/`. It was replaced before deployment and is not presented as a different week on the site.

## Social graphics

Rank movement, sparklines, and team trajectories use hypothetical historical ranks recalculated with the selected week's scoring rule. Each comparison retains that historical week's original game set and prior weight. `comparison_history.py` writes separate `data/comparisons/` files when publishing; original weekly snapshots remain immutable and are still displayed when selected. These comparisons do not use later game results.

Weekly updates generate the latest 1200x630 PNG graphics while retaining older published graphics (FBS Top 10, highest-combined-rating upcoming FBS matchups, and toughest schedules played) in the website's `tanner-ratings/share/SEASON/week-NN/` directory. The page offers PNG downloads and embeds the latest Top 10 in static Open Graph/Twitter metadata for link previews. Week selection changes the on-page graphics; link previews always represent the latest published week. Platforms may cache previews.

To regenerate graphics without recalculating ratings, run `python share_cards.py`. Use `--site PATH` for an alternative website data directory. The bundled Barlow Condensed fonts are distributed under their included SIL Open Font License.

### Team logos

Run `python team_logos.py` to cache logos for all FBS teams in the published snapshots, then `python share_cards.py` to update the graphics. Logos are stored in the sibling website's `tanner-ratings/logos/` folder, so the page and regular graphics build need no external image requests. The index records each ESPN team ID and original image URL. Matching uses school names, with explicit IDs for the ambiguous Charlotte and Troy names. Missing logos fall back to initials on the page. Official school marks retain their respective owners' rights; they are not covered by an open-source code license.

## Resume-style graphics

`profile_metrics.py` calculates two exploratory indices without changing ratings. `share_cards.py` generates their PNGs and a public `profile-metrics.json` audit file. Identical inputs reuse cached calculations; the cache fingerprints the snapshot, priors, solver, and metric source.

- **Brawlers:** candidates are the current FBS Top 50. Consider games with absolute margins below 28 against FBS opponents above the FBS median rating. Refit the entire production model after removing each game, including recomputing game-count weights while preserving priors. Positive rating lifts are multiplied by `(opponent rating - FBS median) / (highest FBS rating - FBS median)` and summed. Negative lifts contribute zero. This is a strength-weighted index, not additive rating points or a change over time.
- **Cupcake Annihilators:** all FBS candidates. For every game, calculate `max(team rating - opponent rating, 0) * max(encoded_margin, 0) / 30.75`, then average across all games. Winning margins saturate at 28 plus the 2.75 bonus; losses and wins against stronger opponents contribute zero. Opponents from every division are included.

The indices are not opposites, not calibrated predictions, and not evidence of overrating. Definitions were explored on the current snapshot, not established via an out-of-sample test. No team-name exceptions are used. Cards include scope, raw index values, records, and game evidence. Exact reconstruction of the published fit is checked before performing leave-one-game-out fits; a changed prior file fails rather than silently using a different baseline.

The graphics publisher also versions the ratings page CSS, JavaScript, and graphic URLs using a content hash. Run `python share_cards.py` after changing those assets and before publishing, so returning visitors fetch a consistent release. JSON requests revalidate cached data.

## Week 5 and historical preservation

Week 5 uses the cumulative `data/raw/2026/week-05.csv` and `--prior-weight 0.75`. Each JSON snapshot records its own model parameters, source hash, prior hash, game results, ratings, ranks, and upcoming predicted lines. Published JSON cannot be replaced with different contents. Earlier CSVs, graphics, and graphic audit files are left untouched during new-week publishing; the week selector reads the original snapshots. Weekly movement compares the actual published rankings, including changes in prior weight. The selected week's method text displays its own prior weight.

## Seen in a New Light

Starting with Week 5, `new_light.py` isolates the revaluation of each FBS team's existing resume. Both comparison fits use the current week's prior weight and corrected historical scores. The second fit adds new results from the rest of the schedule but excludes that team's own new games. The audit retains absolute-change ordering; the graphic separately shows the five biggest positive changes (Under Rated) and five biggest negative changes (Over Rated), ordered within each column. An idle team can qualify. Historical-score corrections and the prior reduction are reported separately and do not contribute to this graphic.

The audit `share/SEASON/week-NN/new-light.json` includes every FBS team's prior effect, historical correction effect, elsewhere-results effect, own-game effect, and past-opponent rating changes. These components sum to the published rating change (within rounding); the own-game effect is applied last, so this is an explicit order-dependent decomposition, not a unique causal allocation. Game-count weights and the entire network are refitted. The past opponent shown on each card is the one with the largest absolute change in the counterfactual fit, as context rather than an additive attribution. No Week 3 snapshot is invented to backfill this graphic for Week 4.

## Home advantage for predictions

`prediction-policy.json` adds 3 points to the home margin for non-neutral fixtures starting with 2026 Week 5. The publisher copies this policy to the website; the upcoming list and share graphic apply the same adjustment. The interactive builder uses home and away inputs and always applies the current 3-point policy, including when exploring historical ratings. The rating fit and immutable snapshot `homeEdge` remain unadjusted, preserving the original model output. Week 4 scheduled predictions are unchanged. The original Week 5 matchup graphic is archived under `archive/prediction-revisions/2026-week05-no-home-advantage/`.

Games to Watch selects the five highest-combined-rating FBS-involving fixtures with a displayed predicted margin of 10 points or less, including the active home adjustment. The full upcoming-game list remains available.

The halftime-blowout experiment is documented in `analysis/results/halftime-2025/README.md`. Its 1.25x variant is now the production default after explicit approval; historical models remain preserved.

## Production halftime rule (Week 5 revision onward)

The CLI defaults to `--margin-model halftime1.25 --prior-weight 0.75`. For the eventual winner, start with min(final margin, 28). If halftime lead is at least 21 and final winning margin at least 10, increase that credit to max(existing credit, min(56, 1.25 * halftime lead)). Then add the unchanged 2.75 winner bonus. Apply signs symmetrically. Missing or invalid quarters fall back to cap28. Validate period totals against final scores, including overtime. Priors retain their original transformation. The 3-point prediction-only home adjustment remains separate.

New snapshots record the margin-model name, parameters, and per-game signed halftime margin (or null), allowing the fit to be reconstructed exactly. Historical snapshots without those fields use cap28. Brawlers refits use each snapshot's model; the descriptive Cupcake index retains its existing capped-final-margin definition. Seen in a New Light compares both sides at the same current model and prior, and records model-change effects separately from results elsewhere. Weekly rank movement still compares actual published rankings, so Week 5 movement includes the model update.

The previous published Week 5 JSON, CSV, graphics, and audits are preserved in `archive/model-revisions/2026-week05-cap28-prior-0.75/`. Published Week 4 is unchanged. To reproduce an older model explicitly, pass `--margin-model cap28` and its saved prior weight. Neither the 2025 prior file nor retrospective experimental results were regenerated with the new rule.
