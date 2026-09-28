"""Walk-forward evaluation of a 28-point Q3 lead / 10-point final lead rule.

Run from any directory: python football/experiments/garbage_time_2025.py
This experiment does not modify production ratings or website data.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ratings import read_csv, select_games, solve


def quarter_margin(game):
    scores = []
    for side in ("Home", "Away"):
        try:
            values = [int(value.strip()) for value in game.get(side + "LineScores", "").split(",")]
        except (TypeError, ValueError):
            return None
        if len(values) < 4 or any(value < 0 for value in values) or sum(values) != game[side + "Points"]:
            return None
        scores.append(sum(values[:3]))
    return scores[0] - scores[1]


def adjusted_margin(game):
    final = game["HomePoints"] - game["AwayPoints"]
    q3 = quarter_margin(game)
    if q3 is not None and abs(q3) >= 28 and final * q3 > 0 and abs(final) >= 10:
        return math.copysign(max(28, abs(final)), final)
    return final


def adjusted_game(game):
    result = dict(game)
    margin = adjusted_margin(game)
    # The production solver only reads these scores to form the margin target.
    # Keep source scores and evaluation outcomes unchanged in the original game.
    result["HomePoints"], result["AwayPoints"] = max(margin, 0), max(-margin, 0)
    return result


def metrics(rows, field):
    errors = np.array([r[field] - r["actualMargin"] for r in rows])
    correct = sum(np.sign(r[field]) == np.sign(r["actualMargin"]) for r in rows)
    return {"games": len(rows), "mae": float(np.mean(abs(errors))), "rmse": float(np.sqrt(np.mean(errors ** 2))), "bias": float(np.mean(errors)), "correct": int(correct), "accuracy": correct / len(rows)}


def summary(rows):
    baseline, candidate = metrics(rows, "baseline"), metrics(rows, "candidate")
    differences = np.array([abs(r["candidate"] - r["actualMargin"]) - abs(r["baseline"] - r["actualMargin"]) for r in rows])
    weeks = sorted({r["week"] for r in rows})
    totals = np.array([sum(d for d, r in zip(differences, rows) if r["week"] == w) for w in weeks])
    counts = np.array([sum(r["week"] == w for r in rows) for w in weeks])
    rng = np.random.default_rng(2025)
    samples = rng.integers(0, len(weeks), size=(10000, len(weeks)))
    boot = totals[samples].sum(axis=1) / counts[samples].sum(axis=1)
    return {"baseline": baseline, "candidate": candidate, "maeChange": float(np.mean(differences)), "maeChangeWeekBootstrap95": np.quantile(boot, [.025, .975]).tolist(), "changedPicks": int(sum(np.sign(r['baseline']) != np.sign(r['candidate']) for r in rows))}


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    data_path = ROOT / "archive/2025/cfbweek15.csv"
    prior_path = ROOT / "archive/2025/MasseyRatings_2024.csv"
    raw = read_csv(data_path)
    games = select_games(raw, 2025, 99)
    priors = {r["Team"]: float(r["MasseyRating"]) for r in read_csv(prior_path)}
    changed = []
    for game in games:
        final = game["HomePoints"] - game["AwayPoints"]
        adjusted = adjusted_margin(game)
        if min(abs(final), 28) != min(abs(adjusted), 28):
            changed.append({"id": game["Id"], "week": int(game["Week"]), "home": game["HomeTeam"], "away": game["AwayTeam"], "homeClass": game["HomeClassification"], "awayClass": game["AwayClassification"], "homeScore": game["HomePoints"], "awayScore": game["AwayPoints"], "q3Margin": quarter_margin(game), "actualMargin": final, "adjustedMargin": adjusted})
    predictions, skipped, time_exclusions = [], [], []
    for week in sorted({int(g["Week"]) for g in games if int(g["Week"]) >= 2}):
        targets = [g for g in games if int(g["Week"]) == week]
        deadline = min(g["StartDate"] for g in targets)
        train = [g for g in games if int(g["Week"]) < week and g["StartDate"] < deadline]
        time_exclusions.extend(g["Id"] for g in games if int(g["Week"]) < week and g["StartDate"] >= deadline)
        baseline = solve(train, priors, prior_weight=1.0)
        candidate = solve([adjusted_game(g) for g in train], priors, prior_weight=1.0)
        for g in targets:
            home, away = g["HomeTeam"], g["AwayTeam"]
            if home not in baseline or away not in baseline:
                skipped.append({"id": g["Id"], "week": week, "home": home, "away": away})
                continue
            predictions.append({"id": g["Id"], "week": week, "home": home, "away": away, "homeClass": g["HomeClassification"], "awayClass": g["AwayClassification"], "actualMargin": g["HomePoints"] - g["AwayPoints"], "baseline": baseline[home] - baseline[away], "candidate": candidate[home] - candidate[away]})
        print(f"Week {week}: {len(train)} training games, {len(targets)} outcomes", flush=True)
    groups = {
        "FBS vs FBS, weeks 4-14": [r for r in predictions if r["week"] >= 4 and r["homeClass"] == r["awayClass"] == "fbs"],
        "FBS vs FBS, weeks 2-14": [r for r in predictions if r["homeClass"] == r["awayClass"] == "fbs"],
        "Any FBS team, weeks 4-14": [r for r in predictions if r["week"] >= 4 and "fbs" in (r["homeClass"], r["awayClass"])],
        "All divisions, weeks 4-14": [r for r in predictions if r["week"] >= 4],
        "All divisions, weeks 2-14": predictions,
    }
    results = {name: summary(rows) for name, rows in groups.items()}
    weekly = []
    for week in range(2, 15):
        rows = [r for r in groups["FBS vs FBS, weeks 2-14"] if r["week"] == week]
        if rows:
            a, b = metrics(rows, "baseline"), metrics(rows, "candidate")
            weekly.append({"week": week, "games": len(rows), "baselineMAE": a["mae"], "candidateMAE": b["mae"], "maeChange": b["mae"] - a["mae"], "baselineCorrect": a["correct"], "candidateCorrect": b["correct"]})
    metadata = {"inputSha256": hashlib.sha256(data_path.read_bytes()).hexdigest(), "priorSha256": hashlib.sha256(prior_path.read_bytes()).hexdigest(), "season": 2025, "weeksAvailable": sorted({int(g["Week"]) for g in games}), "latestGame": max(g["StartDate"] for g in games), "scoredGames": len(games), "validQuarterGames": sum(quarter_margin(g) is not None for g in games), "validQuarterFBSvsFBS": sum(quarter_margin(g) is not None for g in games if g["HomeClassification"] == g["AwayClassification"] == "fbs"), "FBSvsFBSGames": sum(g["HomeClassification"] == g["AwayClassification"] == "fbs" for g in games), "changedGames": len(changed), "changedFBSvsFBSGames": sum(g["homeClass"] == g["awayClass"] == "fbs" for g in changed), "skippedUnratedGames": len(skipped), "timeExclusions": time_exclusions, "modelPriorWeight": 1.0, "results": results}
    out = ROOT / "experiments/results/garbage-time-2025"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    write_csv(out / "predictions.csv", predictions)
    write_csv(out / "adjusted-games.csv", changed)
    write_csv(out / "weekly-fbs.csv", weekly)
    write_csv(out / "skipped-games.csv", skipped)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
