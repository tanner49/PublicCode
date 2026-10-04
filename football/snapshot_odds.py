"""Save an immutable ESPN/DraftKings pregame line snapshot (no bets placed)."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import requests


def main():
    started = datetime.now(timezone.utc)
    output = Path(__file__).parent / 'data' / 'odds-snapshots' / started.strftime('%Y%m%dT%H%M%SZ')
    output.mkdir(parents=True, exist_ok=False)
    rows, sources = [], []
    for day in ('20261002', '20261003', '20261004'):
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?dates={day}&groups=80&limit=200'
        response = requests.get(url, timeout=45)
        response.raise_for_status()
        captured = datetime.now(timezone.utc).isoformat()
        raw = response.content
        (output / f'scoreboard-{day}.json').write_bytes(raw)
        data = response.json()
        assert len(data.get('events', [])) < 200, 'Possible truncated schedule'
        sources.append(dict(url=url, captured_at_utc=captured, sha256=hashlib.sha256(raw).hexdigest()))
        for event in data.get('events', []):
            game = event['competitions'][0]
            teams = {t['homeAway']: t['team'] for t in game['competitors']}
            for odds in game.get('odds') or [{}]:
                spread = odds.get('pointSpread', {})
                total = odds.get('total', {})
                def field(market, side, key):
                    return market.get(side, {}).get('close', {}).get(key, '')
                row = dict(event_id=event['id'], schedule_date=day, kickoff_utc=game['date'],
                           captured_at_utc=captured, status=game['status']['type']['state'],
                           neutral_site=game.get('neutralSite', False),
                           home_id=teams['home']['id'], home=teams['home']['displayName'],
                           away_id=teams['away']['id'], away=teams['away']['displayName'],
                           provider=odds.get('provider', {}).get('name', ''),
                           provider_id=odds.get('provider', {}).get('id', ''),
                           home_spread=field(spread, 'home', 'line'), away_spread=field(spread, 'away', 'line'),
                           home_spread_price=field(spread, 'home', 'odds'), away_spread_price=field(spread, 'away', 'odds'),
                           total=odds.get('overUnder', ''), over_line=field(total, 'over', 'line'),
                           under_line=field(total, 'under', 'line'), over_price=field(total, 'over', 'odds'),
                           under_price=field(total, 'under', 'odds'), details=odds.get('details', ''))
                if row['home_spread'] and row['away_spread']:
                    assert abs(float(row['home_spread']) + float(row['away_spread'])) < .001
                rows.append(row)
    with (output / 'lines.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(started_at_utc=started.isoformat(), sources=sources, games=len({r['event_id'] for r in rows}),
                    rows=len(rows), missing_lines=[r for r in rows if not r['home_spread'] or r['total'] == ''])
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (output / 'README.md').write_text('# Pregame market snapshot\n\n'
        'FBS schedule from ESPN (group 80), October 2–4, 2026, including FBS–FCS games. '
        'Bookmaker names and actual American prices are retained per row. Spreads are signed from each team’s perspective. '
        'Totals are combined points; they are a different market from spreads.\n\n'
        'These are lines available at the recorded capture time, NOT guaranteed final closing lines. '
        'ESPN calls the current quote `close` even before kickoff. No opening-line substitution. '
        'Missing markets remain blank; already-started games have a non-pre status and must not be counted as prospective picks. '
        'Raw responses and SHA-256 hashes are retained for auditing. No wagers were placed.\n', encoding='utf-8')
    print(output.resolve())
    for day in ('20261002', '20261003', '20261004'):
        subset = [r for r in rows if r['schedule_date'] == day]
        print(day, 'games', len(subset), 'spreads', sum(bool(r['home_spread']) for r in subset),
              'totals', sum(r['total'] != '' for r in subset))
    print('Missing:', [(r['away'], r['home']) for r in manifest['missing_lines']])


if __name__ == '__main__':
    main()
