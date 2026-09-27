# Week 4 against the spread

Uses only the archived Week 4 pregame ratings (1.0-game prior), with final scores from the Week 5 snapshot. No Week 5 ratings or 0.75-prior refits enter the predictions. Join on ESPN game ID; all 65 rows matched and each workbook team name was checked against the snapshot school name. Final margins are uncapped, including all scoring; there is no home-field adjustment.

The primary analysis uses the half-point predictions published on the website. Pick the home team when the model home margin exceeds the market home margin, otherwise pick the away team. If equal, record NO EDGE rather than inventing a side. A push would mean the actual margin equals the spread; there were none.

| Scope | ATS wins-losses | No edge | Win rate |
|---|---:|---:|---:|
| Confirmed closing lines | 30-30 | 2 | 50.0% |
| FBS vs FBS, confirmed close | 23-25 | 2 | 47.9% |
| FBS vs FCS, confirmed close | 7-5 | 0 | 58.3% |
| All supplied lines | 31-32 | 2 | 49.2% |

The workbook has 62 Close rows and 3 Latest rows (Air Force/Nevada, Georgia Tech/Stanford, Minnesota/Washington). The Latest rows went 1-2 but are not represented as confirmed closing lines. The six Thursday/Friday matchups omitted from the workbook are listed in summary.json; no lines were invented or substituted for them.

## Rounding sensitivity

Colorado/Baylor: published Baylor -8.5 matched the market. The unrounded prediction was Baylor -8.33, which would select Colorado +8.5; Baylor won by 10, a loss for that pick.

Kansas State/Cincinnati: published Kansas State -6 matched the market. The unrounded prediction was Kansas State -6.13, which would select Kansas State -6; Cincinnati won by 5, another loss.

Thus, using even tiny unrounded model edges instead of published half-point predictions produces **30-32 (48.4%) on confirmed closing lines**. The primary 30-30 result excludes those two negligible-edge games.

## Forecast error and edge size

On the 62 confirmed-close games, mean absolute error against actual final margin was **13.13 points for the published model**, versus **11.81 for the market**. For FBS-vs-FBS games alone, it was 13.29 versus 11.61.

| Absolute model-market disagreement | ATS record | No edge |
|---|---:|---:|
| Under 3 points | 10-8 | 2 |
| 3 to under 7 points | 8-11 | 0 |
| 7+ points | 12-11 | 0 |

These are descriptive buckets, not optimized betting thresholds. This single week shows no clear advantage against the market, and larger disagreements did not consistently improve results.

Reproduce from football/: `python analysis/ats_week04.py`. The workbook is preserved under data/raw/2026/, game-by-game.csv includes every pick and result, and summary.json records input hashes. Workbook statements about the source and line basis are taken as supplied, not independently verified closing prices.

## Three-point home-field adjustment

Add 3 to the archived unrounded predicted home margin for non-neutral games, then round to the nearest half-point. Leave neutral sites unchanged. Apply the same pick and grading rules as above; this is an evaluation only, not a website/model change.

| Confirmed closing lines | No adjustment | Home +3 |
|---|---:|---:|
| All FBS-involving games | 30-30, 2 no edge | 31-29, 2 no edge |
| FBS vs FBS | 23-25, 2 no edge | 23-25, 2 no edge |
| FBS vs FCS | 7-5 | 8-4 |
| Mean absolute margin error | 13.13 | 12.60 |

The market's mean absolute error remains 11.81. Unrounded picks with home +3 go 32-30 versus 30-32 without it. Including the three Latest lines, rounded home-adjusted picks go 32-31 with two no-edge games. The overall ATS improvement comes from the FBS-vs-FCS subset; FBS-vs-FBS remains unchanged in aggregate. Individual selections do change. See home-field-3-game-by-game.csv and home-field-3-summary.json for details.
