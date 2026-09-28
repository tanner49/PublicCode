"""Cache ESPN historical bookmaker responses; do not infer closing lines here."""
import concurrent.futures
import csv
import json
import time
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent / 'data'

def fetch(item):
    year, ident = item
    path = DATA / 'odds' / str(year) / (ident + '.json')
    if path.exists():
        return 'cached'
    url = f'https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/events/{ident}/competitions/{ident}/odds'
    error = ''
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=40)
            response.raise_for_status()
            data = response.json()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding='utf-8')
            return 'downloaded'
        except Exception as exc:
            error = str(exc)
            time.sleep(attempt + 1)
    return f'FAILED {year} {ident}: {error}'

if __name__ == '__main__':
    items = []
    for year in (2023, 2024, 2025):
        with (DATA / f'games_{year}.csv').open(encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                if (row['Completed'] == 'true' and row['HomePoints'] and row['AwayPoints']
                    and 'fbs' in (row['HomeClassification'], row['AwayClassification'])
                    and (row['SeasonType'] != 'regular' or int(row['Week']) >= 4)):
                    items.append((year, row['Id']))
    print(f'Fetching {len(items)} games', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for index, result in enumerate(pool.map(fetch, items), 1):
            if result.startswith('FAILED') or index % 100 == 0:
                print(index, result, flush=True)
