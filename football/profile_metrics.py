"""Descriptive resume styles, not changes to the underlying team ratings."""
import hashlib
import json
from pathlib import Path
from statistics import median

from ratings import encode_margin, read_csv, solve

ROOT = Path(__file__).resolve().parent


def opposition_weight(rating, midpoint, best):
    """Zero at/below the FBS median; one at the highest FBS rating."""
    return min(1.0, max(0.0, (rating - midpoint) / (best - midpoint))) if best > midpoint else 0.0


def dominance_credit(team_rating, opponent_rating, margin):
    """Positive rating gap times the fraction of maximum winning-margin credit."""
    return max(0, team_rating - opponent_rating) * max(0, encode_margin(margin)) / encode_margin(28)


def reconstruct_games(snapshot):
    games = {}
    for team in snapshot['teams']:
        for g in team['games']:
            if g['id'] not in games:
                # Orientation is immaterial: no home adjustment is used in this model.
                games[g['id']] = {'Id': g['id'], 'HomeTeam': team['team'], 'AwayTeam': g['opponent'], 'HomePoints': g['scored'], 'AwayPoints': g['allowed']}
    if len(games) != snapshot['gameCount']:
        raise ValueError('Snapshot game count does not match reconstructed games')
    return list(games.values())


def calculate_profiles(snapshot, cache):
    priors_path = ROOT / 'data/generated' / f"priors-{snapshot['season']-1}.csv"
    prior_bytes = priors_path.read_bytes()
    if hashlib.sha256(prior_bytes).hexdigest() != snapshot['priorSha256']:
        raise ValueError('Prior file differs from the published snapshot baseline')
    fingerprint = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode() + prior_bytes + Path(__file__).read_bytes() + (ROOT / 'ratings.py').read_bytes()).hexdigest()
    if cache.exists():
        stored = json.loads(cache.read_text(encoding='utf-8'))
        if stored.get('fingerprint') == fingerprint:
            return stored
    teams = {t['team']: t for t in snapshot['teams']}
    fbs = [t for t in teams.values() if t['classification'] == 'fbs']
    midpoint = median(t['rating'] for t in fbs)
    best = max(t['rating'] for t in fbs)
    eligible = {t['team'] for t in fbs if t['divisionRank'] <= 50}
    games = reconstruct_games(snapshot)
    priors = {r['Team']: float(r['MasseyRating']) for r in read_csv(priors_path)}
    weight = snapshot['model']['priorWeight']
    baseline = solve(games, priors, prior_weight=weight)
    if any(abs(baseline[n] - t['rating']) > 0.000002 for n, t in teams.items()):
        raise ValueError('Reconstructed fit differs from published ratings')
    lifts = {n: [] for n in eligible}
    for g in games:
        if abs(g['HomePoints'] - g['AwayPoints']) >= 28:
            continue
        relevant = []
        for side, opponent in [('Home', 'Away'), ('Away', 'Home')]:
            name, opp = g[side + 'Team'], g[opponent + 'Team']
            if name in eligible and teams[opp]['classification'] == 'fbs' and teams[opp]['rating'] > midpoint:
                relevant.append((name, opp, g[side + 'Points'] - g[opponent + 'Points']))
        if not relevant:
            continue
        without = solve([x for x in games if x['Id'] != g['Id']], priors, prior_weight=weight)
        for name, opp, margin in relevant:
            if name not in without:
                continue  # No fit exists for a team with no remaining scored games.
            lift = baseline[name] - without[name]
            quality = opposition_weight(teams[opp]['rating'], midpoint, best)
            lifts[name].append({'gameId': g['Id'], 'opponent': opp, 'margin': margin, 'opponentRating': teams[opp]['rating'], 'ratingWithout': without[name], 'lift': lift, 'oppositionWeight': quality, 'contribution': max(0, lift) * quality})
    brawlers = []
    for name in eligible:
        details = sorted(lifts[name], key=lambda g: (-g['contribution'], g['gameId']))
        brawlers.append({'team': name, 'rank': teams[name]['divisionRank'], 'score': sum(g['contribution'] for g in details), 'games': details})
    cupcakes = []
    for t in fbs:
        details = []
        for g in t['games']:
            opp = teams[g['opponent']]
            margin = g['scored'] - g['allowed']
            details.append({'opponent': opp['team'], 'margin': margin, 'ratingGap': max(0, t['rating'] - opp['rating']), 'credit': dominance_credit(t['rating'], opp['rating'], margin)})
        cupcakes.append({'team': t['team'], 'rank': t['divisionRank'], 'score': sum(g['credit'] for g in details) / len(details), 'games': details})
    result = {'fingerprint': fingerprint, 'season': snapshot['season'], 'week': snapshot['week'], 'fbsMedian': midpoint, 'fbsBest': best, 'brawlers': sorted(brawlers, key=lambda t: (-t['score'], t['team'])), 'cupcakes': sorted(cupcakes, key=lambda t: (-t['score'], t['team'])), 'method': {
        'brawlers': 'FBS Top 50 only. For games decided by fewer than 28 points against above-median FBS opponents, refit the full model without each game. Sum positive rating lifts multiplied by (opponent rating - FBS median) / (highest FBS rating - FBS median). Negative lifts contribute zero. This is an index, not additive rating points or weekly movement.',
        'cupcakes': 'All FBS. Average over all games: max(team rating - opponent rating, 0) times max(encoded margin, 0) / 30.75. Encoded margin uses the production 28-point cap and 2.75 winner bonus. Losses and wins over stronger teams contribute zero. Higher means more dominance against weaker opposition, not proof of overrating.',
        'limitations': 'Early-season, current-rating-based descriptive indices. Priors remain in every fit; model game weights are recomputed after removal. These are not validated predictors, nor a causal estimate of schedule choice. The definitions were explored against this snapshot before selecting this version.'}}
    cache.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return result
