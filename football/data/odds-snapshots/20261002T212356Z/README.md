# Pregame market snapshot

FBS schedule from ESPN (group 80), October 2–4, 2026, including FBS–FCS games. Bookmaker names and actual American prices are retained per row. Spreads are signed from each team’s perspective. Totals are combined points; they are a different market from spreads.

These are lines available at the recorded capture time, NOT guaranteed final closing lines. ESPN calls the current quote `close` even before kickoff. No opening-line substitution. Missing markets remain blank; already-started games have a non-pre status and must not be counted as prospective picks. Raw responses and SHA-256 hashes are retained for auditing. No wagers were placed.

## Combined ATS ledger

Use `lines.csv` for the full October 1-3 slate: 59 games, including the two Thursday games. All rows have `include_in_ats=true`. Thursday rows have `status=post` because the lines were retrieved after completion; include them for retrospective ATS grading, not as prospectively locked wagers. `line_provenance` distinguishes the 57 pregame locks from the two retrospective explicit closing lines. `source_path` points to the raw supporting response. The original 57-row CSV is preserved byte-for-byte as `lines-pregame-original.csv`. Do not filter this combined ledger to `status=pre` when grading all games.
