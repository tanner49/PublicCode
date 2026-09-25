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
python ratings.py --input data/raw/2026/week-04.csv --season 2026 --week 4 --rebuild-2025-priors
```

For Week 5, save a cumulative export as `week-05.csv` and run:

```powershell
python ratings.py --input data/raw/2026/week-05.csv --season 2026 --week 5
```

Week 4 means **completed regular-season games through Week 3**. Future fixtures and missing scores never enter the fit. Completed games with missing scores are excluded and their IDs recorded in the snapshot and printed by the command. The export must contain the full season to date, not just the most recent week. `Completed` accepts true/false or 1/0. Invalid nonempty scores and duplicate completed game IDs stop the build.

The command writes JSON and CSV snapshots locally and copies them to the sibling website repo, updating its snapshot index. Override the website data directory with `--site PATH`. Commit/review both repositories and publish the website through its existing GitHub Pages process. No server, API keys, or additional Jekyll plugins are needed. Published snapshots cannot be silently overwritten with changed data; intentional corrections require archiving/removing the affected JSON in both repos first.

## Method

Each game supplies `rating(home) - rating(away) = sign(margin) * (min(abs(margin), 28) + 2.75)`. Ties encode as zero. The old asymmetric cap is fixed for both current ratings and regenerated 2025 priors.

Equations are weighted by `sqrt(2 / (home games + away games + 2 * prior_weight))`. Prior-season ratings act as pseudo-games against zero, with `prior_weight = 1.0` (the original notebook's approximate one-game setting) and the same signed encoding, capped at 100. Their row weight is `sqrt(2 * prior_weight / (team games + prior_weight))`. This normalization treats the zero-rated baseline as having zero games, so the prior is not exactly equal in influence to any particular real game. A sum-to-zero constraint anchors the least-squares solution. The 2026 prior weight was restored to 1.0 at the model owner's request. Rebuilding the 2025 prior CSV still uses the archived final notebook's 0.00005 weight on 2024 ratings, so this change does not retroactively alter the 2025 baseline. No home-field adjustment is applied.

All supplied opponents participate in the fit. The site defaults to FBS; division ranks are calculated within each classification and conference filters retain those ranks. Schedule strength is the mean current rating of played opponents. Per the model owner's choice, rating differences are treated as predicted point margins: excess blowout points are assumed to have no additional predictive value. The website displays the favorite minus the absolute margin, rounded to the nearest half-point (halfway values away from zero), with no home-field adjustment. A zero margin is a pick'em. These are model predictions, not sportsbook prices; no moneyline or win probability is inferred.

Early-season ratings can be volatile. Separate schedule networks are only weakly anchored by priors, so cross-division comparisons deserve caution. Teams without completed games have no rating. No earlier 2026 snapshots are fabricated; movement and history begin with Week 4 and appear as future snapshots are added.

## Files

- `ratings.py`: reusable calculation and publishing command.
- `data/raw/2026/week-04.csv`: exact copy of the supplied Desktop download.
- `data/generated/priors-2025.csv`: corrected ratings from the available 2025 export (regular season through Week 16), using the archived 2024 priors. This is the available export, not a claim of a complete final-season dataset.
- `data/generated/2026/`: immutable weekly ratings in JSON and CSV, including input and prior SHA-256 hashes in JSON.
- `archive/2025/`: original football notebooks and CSVs, moved intact, including pre-existing local edits. To run historical notebooks, open them with this folder as the working directory. Their original model remains for reference.

Run verification with `python -m unittest discover -s tests`.

## Prior implementation history

The archived `cbd.ipynb` calls these "Week 0" pseudo-games against a zero-rated baseline and comments `1.0 ~ one game`. Git commit `32c71d8` used weight 2; `c25e1c0` used 0.5; the preserved local notebook used 0.00005. The 2026 model now uses 1.0. This is an extra least-squares equation per team, not just an initial solver guess. Its relative influence diminishes as actual games accumulate. The prior target retains the original signed encoding (including the winner bonus), rather than inserting the previous rating completely unchanged.

The superseded local Week 4 snapshot with weight 0.00005 is preserved in `archive/model-revisions/2026-week04-prior-0.00005/`. It was replaced before deployment and is not presented as a different week on the site.

## Social graphics

Weekly updates also regenerate 1200x630 PNG graphics (FBS Top 10, highest-combined-rating upcoming FBS matchups, and toughest schedules played) in the website's `tanner-ratings/share/SEASON/week-NN/` directory. The page offers PNG downloads and embeds the latest Top 10 in static Open Graph/Twitter metadata for link previews. Week selection changes the on-page graphics; link previews always represent the latest published week. Platforms may cache previews.

To regenerate graphics without recalculating ratings, run `python share_cards.py`. Use `--site PATH` for an alternative website data directory. The bundled Barlow Condensed fonts are distributed under their included SIL Open Font License.

## Resume-style graphics

`profile_metrics.py` calculates two exploratory indices without changing ratings. `share_cards.py` generates their PNGs and a public `profile-metrics.json` audit file. Identical inputs reuse cached calculations; the cache fingerprints the snapshot, priors, solver, and metric source.

- **Brawlers:** candidates are the current FBS Top 50. Consider games with absolute margins below 28 against FBS opponents above the FBS median rating. Refit the entire production model after removing each game, including recomputing game-count weights while preserving priors. Positive rating lifts are multiplied by `(opponent rating - FBS median) / (highest FBS rating - FBS median)` and summed. Negative lifts contribute zero. This is a strength-weighted index, not additive rating points or a change over time.
- **Cupcake Annihilators:** all FBS candidates. For every game, calculate `max(team rating - opponent rating, 0) * max(encoded_margin, 0) / 30.75`, then average across all games. Winning margins saturate at 28 plus the 2.75 bonus; losses and wins against stronger opponents contribute zero. Opponents from every division are included.

The indices are not opposites, not calibrated predictions, and not evidence of overrating. Definitions were explored on the current snapshot, not established via an out-of-sample test. No team-name exceptions are used. Cards include scope, raw index values, records, and game evidence. Exact reconstruction of the published fit is checked before performing leave-one-game-out fits; a changed prior file fails rather than silently using a different baseline.
