"""Audit the published Week 4 predictions against the supplied odds workbook."""
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/2026/CFB_closing_spreads_2026-09-26.xlsx'
OUT = ROOT / 'analysis/results/2026-week04-ats'


def workbook_rows(path):
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:row', ns):
            cells = {}
            for cell in row.findall('s:c', ns):
                value = cell.find('s:v', ns)
                inline = cell.find('s:is', ns)
                value = value.text if value is not None else ''.join(inline.itertext()) if inline is not None else ''
                if cell.get('t') == 's':
                    value = strings[int(value)]
                cells[''.join(c for c in cell.get('r') if c.isalpha())] = value
            if cells.get('K', '').isdigit():
                yield cells


def summarize(rows):
    wins = sum(r['result'] == 'W' for r in rows)
    losses = sum(r['result'] == 'L' for r in rows)
    return {'games': len(rows), 'wins': wins, 'losses': losses,
            'pushes': sum(r['result'] == 'P' for r in rows),
            'noEdge': sum(r['result'] == 'NO EDGE' for r in rows),
            'winPct': round(100 * wins / (wins + losses), 2) if wins + losses else None,
            'modelMAE': round(sum(abs(r['actualHomeMargin'] - r['modelHomeMargin']) for r in rows) / len(rows), 3) if rows else None,
            'marketMAE': round(sum(abs(r['actualHomeMargin'] - r['marketHomeMargin']) for r in rows) / len(rows), 3) if rows else None}


def main():
    prior_path = ROOT / 'data/generated/2026/week-04.json'
    actual_path = ROOT / 'data/generated/2026/week-05.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    actual = json.loads(actual_path.read_text(encoding='utf-8'))
    fixtures = {g['id']: g for g in prior['fixtures']}
    teams = {t['team']: t for t in actual['teams']}
    rows = []
    seen = set()
    for x in workbook_rows(SOURCE):
        id = x['K']
        assert id not in seen, f'Duplicate workbook game {id}'
        seen.add(id)
        g = fixtures[id]  # Stable ESPN IDs avoid mascot-name matching.
        final = next(r for r in teams[g['home']]['games'] if r['id'] == id)
        assert final['opponent'] == g['away'] and final['week'] == 4
        assert x['E'] in (x['B'], x['C']), x
        assert float(x['F']) <= 0
        market = -float(x['F']) if x['E'] == x['C'] else float(x['F'])
        assert g['homeEdge'] is not None
        raw = g['homeEdge']
        model = math.copysign(math.floor(abs(raw) * 2 + .5) / 2, raw)
        edge = model - market
        actual_margin = final['scored'] - final['allowed']
        picked_home = edge > 0
        cover = (actual_margin - market) * (1 if picked_home else -1)
        result = 'NO EDGE' if edge == 0 else 'P' if cover == 0 else 'W' if cover > 0 else 'L'
        rows.append({'id': id, 'away': g['away'], 'home': g['home'], 'workbookAway': x['B'],
                     'workbookHome': x['C'], 'basis': x['D'], 'bothFBS': g['classification'] == g['awayClassification'] == 'fbs',
                     'modelHomeMargin': model, 'unroundedHomeMargin': raw, 'marketHomeMargin': market,
                     'edge': abs(edge), 'pick': 'PASS' if edge == 0 else g['home'] if picked_home else g['away'],
                     'pickSpread': -market if picked_home else market, 'homeScore': final['scored'],
                     'awayScore': final['allowed'], 'actualHomeMargin': actual_margin, 'result': result,
                     'coverMargin': None if edge == 0 else cover})
    groups = {'all_supplied_lines': rows, 'confirmed_close': [r for r in rows if r['basis'] == 'Close'],
              'latest_not_confirmed_close': [r for r in rows if r['basis'] != 'Close'],
              'fbs_vs_fbs_close': [r for r in rows if r['basis'] == 'Close' and r['bothFBS']],
              'fbs_vs_fcs_close': [r for r in rows if r['basis'] == 'Close' and not r['bothFBS']]}
    for low, high in [(0, 3), (3, 7), (7, 1000)]:
        groups[f'close_edge_{low}_to_{high}'] = [r for r in rows if r['basis'] == 'Close' and low <= r['edge'] < high]
    summary = {name: summarize(group) for name, group in groups.items()}
    summary['sourceHashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, prior_path, actual_path)}
    summary['uncoveredFBSFixtures'] = [g for g in prior['fixtures'] if (g['classification'] == 'fbs' or g['awayClassification'] == 'fbs') and g['id'] not in seen]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'game-by-game.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
