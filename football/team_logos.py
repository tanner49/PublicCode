"""Cache FBS logos for the website and graphics; run separately from ratings."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from pathlib import Path
import unicodedata
from urllib.request import urlopen

from PIL import Image

DIRECTORY = 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=1000'


def normalize(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', name) if not unicodedata.combining(c)).casefold()


def refresh(site):
    with urlopen(DIRECTORY, timeout=30) as response:
        directory = json.load(response)['sports'][0]['leagues'][0]['teams']
    lookup = {}
    for row in directory:
        team = row['team']
        lookup.setdefault(normalize(team['location']), []).append(team)
    manifest = json.loads((site / 'data/index.json').read_text())
    names = set()
    for entry in manifest['snapshots']:
        snapshot = json.loads((site / 'data' / entry['path']).read_text(encoding='utf-8'))
        names.update(t['team'] for t in snapshot['teams'] if t['classification'] == 'fbs')
    folder = site / 'logos'
    folder.mkdir(exist_ok=True)

    def download(name):
        matches = lookup.get(normalize(name), [])
        explicit_ids = {'Charlotte': '2429', 'Troy': '2653'}
        if name in explicit_ids:
            matches = [t for t in matches if t['id'] == explicit_ids[name]]
        if len(matches) != 1:
            raise ValueError(f'Needs explicit logo match: {name}')
        team = matches[0]
        url = next(logo['href'] for logo in team['logos'] if 'default' in logo['rel'])
        path = folder / f"{team['id']}.png"
        if not path.exists():
            with urlopen(url, timeout=30) as response:
                image = Image.open(BytesIO(response.read())).convert('RGBA')
            image.thumbnail((160, 160), Image.Resampling.LANCZOS)
            image.save(path, optimize=True)
        return name, {'path': f'logos/{path.name}', 'source': url, 'espnId': team['id']}

    with ThreadPoolExecutor(max_workers=8) as pool:
        logos = dict(pool.map(download, sorted(names)))
    (folder / 'index.json').write_text(json.dumps(logos, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Cached logos for {len(logos)} FBS teams.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=Path(__file__).resolve().parents[2] / 'tanner49.github.io/tanner-ratings')
    refresh(parser.parse_args().site)
