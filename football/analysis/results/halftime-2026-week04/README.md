# 2026 Week 4: halftime1.25 versus cap28, controlled settings

Both models train only on the exact original Week 4 CSV (completed 2026 games through Week 3), use the same archived 2025 priors at weight 0.75, and add 3 points to the home prediction except at neutral sites. The sole model difference is the previously defined halftime1.25 target rule. Historical production Week 4 used prior 1.0, so this newly refitted baseline is not the earlier published baseline. Nothing is changed on the website.

Training: 1,062 games, 882 with internally consistent quarter scores. Missing or inconsistent quarters fall back to cap28. The halftime rule changes 219 targets. Source and prior hashes are verified against the saved Week 4 snapshot, and every training kickoff precedes Week 4's first fixture. Only final scores, line metadata and matchup identities from the evaluation files are used for grading; Week 5 ratings never enter training.

| Confirmed closing lines | Cap28 | Halftime1.25 |
|---|---:|---:|
| All 62 games | 30-28, 4 passes | 35-26, 1 pass |
| Win percentage excluding passes | 51.7% | 57.4% |
| FBS vs FBS | 23-24, 3 passes | 27-22, 1 pass |
| FBS vs FCS | 7-4, 1 pass | 8-4 |
| Unrounded ATS, all 62 | 30-32 | 36-26 |
| Unrounded margin MAE | 12.69 | 11.95 |
| Underdog selections, all 62 | 37 | 31 |

Rounded primary predictions use two decimals then the site's nearest-half-point rounding rule. Equality with the market is a pass, not a push; there are no pushes. On the 57 games where both rounded versions make a pick, baseline goes 30-27 and halftime goes 32-25. Thus the improvement is not only about converting passes into selections, but the full headline improvement partly reflects that change in participation.

The market's MAE on these games is 11.81. Including three lines labeled Latest rather than Close yields baseline 31-30 with four passes versus halftime 36-28 with one pass. Those rows are kept separate from confirmed-close results.

This is a favorable retrospective check, not fresh prospective validation: Week 4 outcomes have already been examined while discussing the model. The 1.25 multiplier and guardrails were unchanged from the 2025 experiment, and both models use identical settings apart from their margin targets. No significance or persistent advantage is claimed from this week.

Reproduce from football/: `python analysis/halftime_2026_week04.py`. Fitted ratings and every graded game are saved alongside summary.json. The side model is not deployed.
