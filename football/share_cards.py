"""Render accurate, reusable social graphics directly from published snapshots."""
import hashlib
import html
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent / 'fonts'
INK, PAPER, LIME, ORANGE, MUTED = '#172d25', '#f5f4ed', '#d9f18b', '#f08055', '#b6c6ba'


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ('BarlowCondensed-Bold.ttf' if bold else 'BarlowCondensed-Regular.ttf')), size)


def text(draw, xy, label, size=26, color=PAPER, bold=False, width=None, anchor='lt'):
    label = str(label)
    face = font(size, bold)
    while width and draw.textlength(label, font=face) > width and size > 14:
        size -= 1
        face = font(size, bold)
    draw.text(xy, label, font=face, fill=color, anchor=anchor)


def canvas(snapshot, title, subtitle):
    image = Image.new('RGB', (1200, 630), INK)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1200, 9), fill=LIME)
    text(draw, (42, 29), 'THE “PROVE IT” RANKINGS', 23, LIME, True)
    text(draw, (1158, 29), f"{snapshot['season']}  ·  WEEK {snapshot['week']}", 25, LIME, True, anchor='rt')
    text(draw, (40, 66), title, 87, bold=True, width=1100)
    text(draw, (43, 163), subtitle, 25, MUTED)
    draw.line((42, 570, 1158, 570), fill='#47604e', width=1)
    text(draw, (42, 591), 'COLLEGE FOOTBALL', 22, LIME, True)
    text(draw, (1158, 591), 'tanner49.github.io/tanner-ratings', 23, PAPER, anchor='rt')
    return image, draw


def record(team):
    return f"{team['wins']}–{team['losses']}" + (f"–{team['ties']}" if team['ties'] else '')


def render_cards(snapshot, site):
    folder = site / 'share' / str(snapshot['season']) / f"week-{snapshot['week']:02}"
    folder.mkdir(parents=True, exist_ok=True)
    teams = sorted((t for t in snapshot['teams'] if t['classification'] == 'fbs'), key=lambda t: (-t['rating'], t['team']))
    image, draw = canvas(snapshot, 'THE TOP 10.', f"FBS | Results through Week {snapshot['throughWeek']}")
    for i, team in enumerate(teams[:10]):
        x, y = 42 + (i // 5) * 578, 215 + (i % 5) * 67
        draw.rectangle((x, y - 5, x + 538, y + 55), fill='#243c2e')
        text(draw, (x + 12, y + 3), f'{i+1:02}', 40, LIME if i < 3 else MUTED, True)
        text(draw, (x + 74, y + 1), team['team'], 35, bold=True, width=330)
        text(draw, (x + 74, y + 37), record(team), 20, MUTED)
        text(draw, (x + 522, y + 5), f"{team['rating']:.2f}", 33, LIME, True, anchor='rt')
    image.save(folder / 'top10.png', optimize=True)

    ratings = {t['team']: t['rating'] for t in snapshot['teams']}
    fixtures = [g for g in snapshot['fixtures'] if g['home'] in ratings and g['away'] in ratings and (g['classification'] == 'fbs' or g['awayClassification'] == 'fbs')]
    fixtures.sort(key=lambda g: (-(ratings[g['home']] + ratings[g['away']]), g['date'], g['id']))
    image, draw = canvas(snapshot, 'THE GAMES TO WATCH.', 'Top FBS matchups | Predicted lines')
    for i, game in enumerate(fixtures[:5]):
        y = 218 + i * 66
        draw.line((42, y + 54, 1158, y + 54), fill='#334c3b')
        text(draw, (45, y), f'{i+1:02}', 40, LIME, True)
        matchup = f"{game['away']} {'vs.' if game['neutral'] else 'at'} {game['home']}"
        text(draw, (112, y), matchup, 35, bold=True, width=690)
        margin = game['homeEdge']
        points = math.floor(abs(margin) * 2 + .5) / 2
        line = "Pick’em" if not points else f"{game['home'] if margin > 0 else game['away']} −{points:.1f}"
        text(draw, (1158, y + 10), line, 29, LIME, True, width=330, anchor='rt')
    if not fixtures:
        text(draw, (42, 270), 'No upcoming matchups available for this week.', 38)
    image.save(folder / 'matchups.png', optimize=True)

    image, draw = canvas(snapshot, 'THE HARDEST ROADS.', f"FBS | Average opponent rating through Week {snapshot['throughWeek']}")
    schedules = sorted(teams, key=lambda t: (-t['scheduleStrength'], t['team']))[:5]
    for i, team in enumerate(schedules):
        y = 216 + i * 66
        draw.line((42, y + 55, 1158, y + 55), fill='#334c3b')
        text(draw, (45, y), f'{i+1:02}', 40, ORANGE, True)
        text(draw, (112, y), team['team'], 36, bold=True, width=510)
        text(draw, (114, y + 38), f"{record(team)} record", 20, MUTED)
        strength = team['scheduleStrength']
        text(draw, (1158, y + 2), f'{strength:.2f}', 38, PAPER, True, anchor='rt')
    image.save(folder / 'schedules.png', optimize=True)
    render_profile_cards(snapshot, folder)
    return folder


def render_profile_cards(snapshot, folder):
    from profile_metrics import calculate_profiles
    profiles = calculate_profiles(snapshot, folder / 'profile-metrics.json')
    teams = {t['team']: t for t in snapshot['teams']}
    for kind, title, subtitle, color in [
        ('brawlers', 'THE BRAWLERS.', 'Tough games. Well-earned respect.', LIME),
        ('cupcakes', 'CUPCAKE ANNIHILATORS.', 'Big wins against easier competition.', ORANGE),
    ]:
        rows = [r for r in profiles[kind] if r['score'] > 0]
        image, draw = canvas(snapshot, title, subtitle)
        draw.rectangle((40, 582, 520, 629), fill=INK)
        text(draw, (42, 591), 'FBS TOP 50' if kind == 'brawlers' else 'ALL FBS TEAMS', 22, LIME, True)
        for i, row in enumerate(rows[:5]):
            t = teams[row['team']]
            y = 211 + i * 64
            draw.line((42, y + 55, 1158, y + 55), fill='#334c3b')
            text(draw, (45, y), f'{i+1:02}', 40, color, True)
            text(draw, (112, y), row['team'], 35, bold=True, width=690)
            if kind == 'brawlers':
                g = row['games'][0]
                result = 'W' if g['margin'] > 0 else 'L' if g['margin'] < 0 else 'T'
                detail = f"{record(t)} | {result} by {abs(g['margin'])} vs {g['opponent']}"
            else:
                max_wins = sum(g['margin'] >= 28 and g['ratingGap'] > 0 for g in row['games'])
                detail = f"{record(t)} | {max_wins} wins by 28+ over weaker opponents"
            text(draw, (114, y + 38), detail, 23, MUTED, width=850)
            text(draw, (1158, y + 2), f"{row['score']:.1f}", 38, color, True, anchor='rt')
            text(draw, (1158, y + 41), 'SCORE', 15, MUTED, anchor='rt')
        image.save(folder / f'{kind}.png', optimize=True)


def publish_share_cards(data_directory):
    site = data_directory.parent
    manifest = json.loads((data_directory / 'index.json').read_text(encoding='utf-8'))
    entries = sorted(manifest['snapshots'], key=lambda s: (s['season'], s['week']))
    for entry in entries:
        snapshot = json.loads((data_directory / entry['path']).read_text(encoding='utf-8'))
        folder = render_cards(snapshot, site)
    if not entries:
        return
    relative = (folder / 'top10.png').relative_to(site).as_posix()
    version = hashlib.sha256((folder / 'top10.png').read_bytes()).hexdigest()[:12]
    image_url = f'https://tanner49.github.io/tanner-ratings/{relative}?v={version}'
    title = f"The “Prove It” Rankings | {snapshot['season']} Week {snapshot['week']}"
    description = f"FBS Top 10, Week {snapshot['week']} predictions, and toughest schedules. Results through Week {snapshot['throughWeek']}."
    tags = {'og:type': 'website', 'og:site_name': 'The “Prove It” Rankings', 'og:title': title, 'og:description': description, 'og:url': 'https://tanner49.github.io/tanner-ratings/', 'og:image': image_url, 'og:image:secure_url': image_url, 'og:image:type': 'image/png', 'og:image:width': '1200', 'og:image:height': '630', 'og:image:alt': f"{snapshot['season']} Week {snapshot['week']} FBS Top 10 Prove It Rankings", 'twitter:card': 'summary_large_image', 'twitter:title': title, 'twitter:description': description, 'twitter:image': image_url, 'twitter:image:alt': f"{snapshot['season']} Week {snapshot['week']} FBS Top 10 Prove It Rankings"}
    block = '<!-- social-preview:start -->\n' + '\n'.join(f'  <meta {"name" if key.startswith("twitter:") else "property"}="{key}" content="{html.escape(value, quote=True)}">' for key, value in tags.items()) + '\n  <!-- social-preview:end -->'
    path = site / 'index.html'
    if path.exists():
        source = path.read_text(encoding='utf-8')
        if '<!-- social-preview:start -->' in source:
            source = re.sub(r'<!-- social-preview:start -->.*?<!-- social-preview:end -->', lambda _: block, source, flags=re.S)
        else:
            source = source.replace('</head>', '  ' + block + '\n</head>')
        source = re.sub(r'(id="share-image" src=")[^"]+', lambda m: m[1] + relative, source)
        source = re.sub(r'(<img id="share-image"[^>]*alt=")[^"]*', lambda m: m[1] + html.escape(tags['og:image:alt'], quote=True), source)
        source = re.sub(r'(id="share-download" href=")[^"]+', lambda m: m[1] + relative, source)
        path.write_text(source, encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=Path(__file__).resolve().parents[2] / 'tanner49.github.io/tanner-ratings/data')
    publish_share_cards(parser.parse_args().site)
