"""Exploratory comparison of frozen Week 4 forecasts with supplied closing lines."""
import csv
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/results/2026-week04-ats'


def fit(x, y):
    return np.linalg.lstsq(x, y, rcond=None)[0]


def correlation(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def study(rows, home_adjustment):
    market = np.array([float(r['marketHomeMargin']) for r in rows])
    model = np.array([float(r['unroundedHomeMargin']) for r in rows])
    snapshot = json.loads((ROOT / 'data/generated/2026/week-04.json').read_text(encoding='utf-8'))
    neutral = {g['id']: g['neutral'] for g in snapshot['fixtures']}
    model += np.array([0 if neutral[r['id']] else home_adjustment for r in rows])
    actual = np.array([float(r['actualHomeMargin']) for r in rows])
    fcs = np.array([r['bothFBS'] != 'True' for r in rows], dtype=float)
    delta = model - market
    sign = np.sign(market)
    # A home/away offset, market-margin compression, and separate FCS effect.
    x = np.column_stack([np.ones(len(rows)), market, sign * fcs])
    if not fcs.any():
        x = x[:, :2]
    coeff = fit(x, delta)
    fitted = x @ coeff
    loo = np.array([x[i] @ fit(np.delete(x, i, 0), np.delete(delta, i)) for i in range(len(rows))])
    # Test the part of disagreement not explained by the above simple structure.
    unique = delta - fitted
    design = np.column_stack([x, unique])
    market_error = actual - market
    beta = fit(design, market_error)[-1]
    rng = np.random.default_rng(20260926)
    samples = []
    slopes = []
    for _ in range(10000):
        ix = rng.integers(0, len(rows), len(rows))
        # Refit structural controls inside each bootstrap resample.
        samples.append(float(fit(design[ix], market_error[ix])[-1]))
        slopes.append(float(1 + fit(x[ix], delta[ix])[1]))
    favorite_model = sign * model
    magnitude = abs(market)
    bins = []
    for lower, upper in [(0, 7), (7, 14), (14, 1000)]:
        mask = (magnitude >= lower) & (magnitude < upper)
        if mask.any():
            bins.append({'spreadRange': [lower, upper], 'games': int(mask.sum()),
                         'marketFavoriteMargin': float(magnitude[mask].mean()),
                         'modelFavoriteMargin': float(favorite_model[mask].mean()),
                         'difference': float((favorite_model-magnitude)[mask].mean())})
    # Shuffle picks among games with comparable market spreads and division types.
    # This retains the model's broad favorite/underdog preferences in each group.
    rounded = np.sign(model) * np.floor(abs(model)*2 + .5)/2
    picks = np.sign(rounded-market) * sign
    covers = np.sign(actual-market) * sign
    strata = [(int(fcs[i]), int(np.digitize(magnitude[i], [7, 14]))) for i in range(len(rows))]
    groups = [np.array([i for i, key in enumerate(strata) if key == group]) for group in sorted(set(strata))]
    observed_wins = int((picks*covers > 0).sum())
    randomized_wins = []
    for _ in range(10000):
        shuffled = picks.copy()
        for group in groups:
            shuffled[group] = rng.permutation(picks[group])
        randomized_wins.append(int((shuffled*covers > 0).sum()))
    return {'n': len(rows), 'homeAdjustment': home_adjustment,
            'correlationWithMarket': correlation(model, market),
            'meanAbsoluteDisagreement': float(abs(delta).mean()),
            'disagreementAtLeast7': int((abs(delta) >= 7).sum()),
            'samePredictedWinner': int((np.sign(model) == np.sign(market)).sum()),
            'marketSlope': float(1 + coeff[1]), 'marketSlopeBootstrap95': list(map(float, np.percentile(slopes, [2.5,97.5]))), 'homeOffset': float(coeff[0]),
            'extraFCSFavoriteCompression': float(coeff[2]) if len(coeff) > 2 else None,
            'structuralDisagreementR2': float(1 - np.sum((delta-fitted)**2)/np.sum((delta-delta.mean())**2)),
            'structuralDisagreementLOOR2': float(1 - np.sum((delta-loo)**2)/np.sum((delta-delta.mean())**2)),
            'remainingDisagreementSD': float(np.std(unique, ddof=1)),
            'disagreementVsMarketErrorCorrelation': correlation(delta, market_error),
            'uniqueDisagreementOutcomeCoefficient': float(beta),
            'uniqueCoefficientBootstrap95': list(map(float, np.percentile(samples, [2.5, 97.5]))),
            'modelMAE': float(abs(actual-model).mean()), 'marketMAE': float(abs(actual-market).mean()),
            'favoriteMarginBins': bins, 'shuffledPicks': {'observedWins': observed_wins, 'noPicks': int((picks==0).sum()), 'meanRandomizedWins': float(np.mean(randomized_wins)), 'randomizedWins95': list(map(float, np.percentile(randomized_wins,[2.5,97.5]))), 'fractionAtLeastObserved': float(np.mean(np.array(randomized_wins)>=observed_wins)), 'stratumSizes': [len(g) for g in groups]}}


def main():
    rows = [r for r in csv.DictReader((OUT / 'game-by-game.csv').open(encoding='utf-8')) if r['basis'] == 'Close']
    result = {name: study(subset, adjustment) for name, subset, adjustment in [
        ('all_original', rows, 0), ('all_home3', rows, 3),
        ('fbs_only_original', [r for r in rows if r['bothFBS'] == 'True'], 0),
        ('fbs_only_home3', [r for r in rows if r['bothFBS'] == 'True'], 3)]}
    (OUT / 'market-structure.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
