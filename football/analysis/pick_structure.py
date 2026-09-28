"""Test the structure of ATS choices independently of game outcomes.

Exploratory: hypotheses follow examination of this week's data. Fixed seed,
fixed ridge penalty, no tuning to outcomes or classification accuracy.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / 'results/2026-week04-ats'
REPS = 20000


def fair_coin_p(k, n):
    return min(1., 2 * sum(math.comb(n, i) for i in range(max(k, n-k), n+1)) / 2**n)


def study(rows, adjusted=True):
    pick_key = 'adjustedPick' if adjusted else 'pick'
    result_key = 'adjustedResult' if adjusted else 'result'
    rows = [r for r in rows if r[pick_key] != 'PASS']
    v = np.array([float(r['marketHomeMargin']) for r in rows])
    mag = abs(v)
    fcs = np.array([r['bothFBS'] != 'True' for r in rows])
    # +1 means taking the underdog against the spread, -1 means favorite.
    y = np.array([1. if r[pick_key] != (r['home'] if v[i] > 0 else r['away']) else -1.
                  for i, r in enumerate(rows)])
    features = np.column_stack([mag, v > 0, fcs])
    features = features[:, features.std(axis=0) > 0]
    z = (features-features.mean(axis=0))/features.std(axis=0)
    x = np.column_stack([np.ones(len(rows)), z])
    penalty = np.eye(x.shape[1]); penalty[0, 0] = 0
    h = x @ np.linalg.solve(x.T @ x + penalty, x.T)
    # Exact LOO ridge scores: a game's own label never predicts itself.
    loo = h.copy(); np.fill_diagonal(loo, 0)
    loo /= (1 - np.diag(h))[:, None]
    def scores(labels):
        predicted = loo @ labels > 0
        actual = labels > 0
        return .5 * ((predicted & actual).sum(axis=0)/actual.sum(axis=0)
                     + (~predicted & ~actual).sum(axis=0)/(~actual).sum(axis=0))
    observed = float(scores(y))
    rng = np.random.default_rng(9272026)
    shuffled = np.column_stack([rng.permutation(y) for _ in range(REPS)])
    null_scores = scores(shuffled)
    big = mag >= 14
    contrast = float((y[big] > 0).mean() - (y[~big] > 0).mean())
    null_contrast = (shuffled[big] > 0).mean(axis=0) - (shuffled[~big] > 0).mean(axis=0)
    def group(mask):
        selected = [r for i, r in enumerate(rows) if mask[i]]
        return {'games': int(mask.sum()), 'underdogPicks': int(((y > 0) & mask).sum()),
                'wins': sum(r[result_key] == 'W' for r in selected),
                'losses': sum(r[result_key] == 'L' for r in selected)}
    prediction = loo @ y > 0
    return {'gamesWithPicks': len(rows), 'underdogPicks': int((y > 0).sum()),
            'fairCoinTwoSidedP': fair_coin_p(int((y > 0).sum()), len(rows)),
            'largeSpread14Plus': group(big), 'smallerSpread': group(~big),
            'underdogRateDifference': contrast,
            'rateDifferencePermutationP': float((1 + (abs(null_contrast) >= abs(contrast)-1e-12).sum())/(REPS+1)),
            'LOOBalancedAccuracy': observed,
            'LOOCorrect': int((prediction == (y > 0)).sum()),
            'LOOActualUnderdogsCorrect': int((prediction & (y > 0)).sum()),
            'LOOActualFavoritesCorrect': int((~prediction & (y < 0)).sum()),
            'permutedLOOBalancedAccuracyMean': float(null_scores.mean()),
            'LOOPermutationP': float((1 + (null_scores >= observed-1e-12).sum())/(REPS+1)),
            'nullDescription': 'Shuffle choices across games while preserving total underdog/favorite counts. Outcome-blind features: market spread magnitude, market favorite is home, FBS-vs-FCS. Ridge penalty 1; exact leave-one-out predictions; balanced accuracy averages favorite and underdog recall. Covariate scaling uses the entire fixed design matrix, never game outcomes.'}


def main():
    rows = [r for r in csv.DictReader((OUT / 'home-field-3-game-by-game.csv').open(encoding='utf-8')) if r['basis'] == 'Close']
    result = {name: study(subset, adjusted) for name, subset, adjusted in [
        ('home3_all', rows, True), ('home3_fbs_only', [r for r in rows if r['bothFBS'] == 'True'], True),
        ('original_all', rows, False), ('original_fbs_only', [r for r in rows if r['bothFBS'] == 'True'], False)]}
    (OUT / 'pick-structure.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
