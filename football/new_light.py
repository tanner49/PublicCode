"""Revalue an unchanged resume using the new results elsewhere in the schedule."""
import hashlib
import json
from pathlib import Path

from profile_metrics import reconstruct_games
from ratings import read_csv, solve

ROOT = Path(__file__).resolve().parent


def signature(game):
    return tuple(sorted([(game['HomeTeam'], game['HomePoints']),
                         (game['AwayTeam'], game['AwayPoints'])]))


def analyze(previous, current, priors):
    old = reconstruct_games(previous)
    games = reconstruct_games(current)
    old_ids = {g['Id']: signature(g) for g in old}
    current_ids = {g['Id']: signature(g) for g in games}
    if any(key not in current_ids for key in old_ids):
        raise ValueError('Historical games disappeared; supply the full season export.')
    corrections = [key for key, value in old_ids.items() if current_ids[key] != value]
    corrected_old = [g for g in games if g['Id'] in old_ids]
    new = [g for g in games if g['Id'] not in old_ids]
    weight = current['model']['priorWeight']
    # Both sides of the comparison use this week's prior weight.
    before_corrections = solve(old, priors, prior_weight=weight)
    baseline = solve(corrected_old, priors, prior_weight=weight)
    full = solve(games, priors, prior_weight=weight)
    old_teams = {t['team']: t for t in previous['teams']}
    if any(abs(full[t['team']] - t['rating']) > 2e-6 for t in current['teams']):
        raise ValueError('Reconstructed Week 5 fit differs from published ratings')
    rows = []
    for team in current['teams']:
        name = team['team']
        if team['classification'] != 'fbs' or name not in old_teams:
            continue
        elsewhere = [g for g in new if name not in (g['HomeTeam'], g['AwayTeam'])]
        updated = solve(corrected_old + elsewhere, priors, prior_weight=weight) if elsewhere else baseline
        effect = updated[name] - baseline[name]
        opponents = sorted({g['opponent'] for g in old_teams[name]['games']})
        evidence = sorted([{'team': opp, 'before': baseline[opp], 'after': updated[opp],
                            'change': updated[opp] - baseline[opp]} for opp in opponents],
                          key=lambda r: (-abs(r['change']), r['team']))
        rows.append({'team': name, 'change': effect, 'previousPublishedRating': old_teams[name]['rating'],
                     'baselineRating': baseline[name], 'revaluedRating': updated[name],
                     'currentPublishedRating': team['rating'],
                     'priorChange': before_corrections[name] - old_teams[name]['rating'],
                     'historicalCorrectionEffect': baseline[name] - before_corrections[name],
                     'ownGameEffect': full[name] - updated[name],
                     'excludedOwnGameIds': [g['Id'] for g in new if name in (g['HomeTeam'], g['AwayTeam'])],
                     'previousOpponents': evidence})
    return {'season': current['season'], 'week': current['week'], 'previousWeek': previous['week'],
            'priorWeight': weight, 'newGames': len(new), 'correctedHistoricalGameIds': corrections,
            'teams': sorted(rows, key=lambda r: (-abs(r['change']), r['team'])),
            'method': 'FBS teams present in both weeks. Refit the previous games with any corrected scores and the current prior weight. Add all newly recorded games except the focal team\'s own games and refit. The difference is the signed change in rating points from results elsewhere. Sort by absolute change, including upgrades and downgrades. The focal team\'s previous results stay fixed. Prior-weight changes and historical score corrections are excluded. Game-count weights and the full schedule network are recomputed, so this includes indirect opponent effects and normalization, not only a simple average of opponent-rating changes. The own-game contribution is added last; this decomposition is order-dependent. Opponent changes shown are context, not additive contributions.'}


def calculate_new_light(previous, current, cache):
    prior_path = ROOT / 'data/generated' / f"priors-{current['season']-1}.csv"
    prior_bytes = prior_path.read_bytes()
    if any(s['priorSha256'] != hashlib.sha256(prior_bytes).hexdigest() for s in (previous, current)):
        raise ValueError('Prior file does not match the historical snapshots')
    fingerprint = hashlib.sha256(json.dumps([previous, current], sort_keys=True).encode() + prior_bytes
                                 + Path(__file__).read_bytes() + (ROOT / 'ratings.py').read_bytes()
                                 + (ROOT / 'profile_metrics.py').read_bytes()).hexdigest()
    if cache.exists():
        stored = json.loads(cache.read_text(encoding='utf-8'))
        if stored.get('fingerprint') == fingerprint:
            return stored
    priors = {r['Team']: float(r['MasseyRating']) for r in read_csv(prior_path)}
    result = analyze(previous, current, priors)
    result['fingerprint'] = fingerprint
    cache.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    return result
