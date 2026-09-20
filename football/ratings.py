"""Reproducible Tanner Ratings snapshots. Run --help for the weekly workflow."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
PRIOR_WEIGHT = 1.0
HISTORICAL_2025_PRIOR_WEIGHT = 0.00005
BONUS = 2.75


def encode_margin(margin, cap=28):
    return math.copysign(min(abs(margin), cap) + BONUS, margin) if margin else 0.0


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def truth(value):
    return str(value).strip().lower() in {"true", "1"}


def select_games(rows, season, through_week):
    games, seen = [], set()
    required = {"Id", "Season", "Week", "Completed", "SeasonType", "HomeTeam", "AwayTeam", "HomePoints", "AwayPoints"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("CSV is empty or missing required columns: " + ", ".join(sorted(required)))
    for row in rows:
        if int(row["Season"]) != season or int(row["Week"]) > through_week or row["SeasonType"] != "regular" or not truth(row["Completed"]):
            continue
        if not row["HomePoints"].strip() or not row["AwayPoints"].strip():
            continue  # Preserve the notebook's exclusion of unscored completed games.
        if row["Id"] in seen:
            raise ValueError(f"Duplicate completed game: {row['Id']}")
        seen.add(row["Id"])
        game = dict(row)
        for field in ("HomePoints", "AwayPoints"):
            score = float(row[field])
            if not math.isfinite(score) or score < 0 or not score.is_integer():
                raise ValueError(f"Invalid score in game {row['Id']}: {field}")
            game[field] = int(score)
        if not row["HomeTeam"] or not row["AwayTeam"] or row["HomeTeam"] == row["AwayTeam"]:
            raise ValueError(f"Invalid teams in game {row['Id']}")
        games.append(game)
    if not games:
        raise ValueError("No completed regular-season games in the requested season/week range")
    return games


def solve(games, priors, prior_weight=PRIOR_WEIGHT):
    teams = sorted({g[side + "Team"] for g in games for side in ("Home", "Away")})
    indices = {team: i for i, team in enumerate(teams)}
    counts = {team: 0 for team in teams}
    for game in games:
        for side in ("Home", "Away"):
            counts[game[side + "Team"]] += 1
    rows, targets = [], []
    for game in games:
        home, away = game["HomeTeam"], game["AwayTeam"]
        weight = math.sqrt(2 / (counts[home] + counts[away] + 2 * prior_weight))
        row = np.zeros(len(teams))
        row[indices[home]], row[indices[away]] = weight, -weight
        rows.append(row)
        targets.append(encode_margin(game["HomePoints"] - game["AwayPoints"]) * weight)
    for team, prior in priors.items():
        if team not in indices:
            continue
        weight = math.sqrt(prior_weight * 2 / (counts[team] + prior_weight))
        row = np.zeros(len(teams))
        row[indices[team]] = weight
        rows.append(row)
        targets.append(encode_margin(prior, cap=100) * weight)
    rows.append(np.ones(len(teams)))
    targets.append(0)
    ratings = np.linalg.lstsq(np.vstack(rows), np.array(targets), rcond=None)[0]
    return dict(zip(teams, map(float, ratings)))


def build_snapshot(rows, season, week, priors, source_hash):
    games = select_games(rows, season, week - 1)
    ratings = solve(games, priors)
    teams = {name: {"team": name, "rating": round(rating, 6), "classification": "unknown", "conference": "Independent", "wins": 0, "losses": 0, "ties": 0, "games": []} for name, rating in ratings.items()}
    for game in sorted(games, key=lambda g: (g["StartDate"], g["Id"])):
        for side, opponent in (("Home", "Away"), ("Away", "Home")):
            team = teams[game[side + "Team"]]
            team["classification"] = game.get(side + "Classification") or "unknown"
            team["conference"] = game.get(side + "Conference") or "Independent"
            scored, allowed = game[side + "Points"], game[opponent + "Points"]
            result = "W" if scored > allowed else "L" if scored < allowed else "T"
            team[{"W": "wins", "L": "losses", "T": "ties"}[result]] += 1
            team["games"].append({"id": game["Id"], "week": int(game["Week"]), "date": game["StartDate"], "opponent": game[opponent + "Team"], "venue": "N" if truth(game.get("NeutralSite")) else "H" if side == "Home" else "A", "scored": scored, "allowed": allowed, "result": result})
    ordered = sorted(teams.values(), key=lambda t: (-t["rating"], t["team"]))
    ranks = {}
    for rank, team in enumerate(ordered, 1):
        division = team["classification"]
        ranks[division] = ranks.get(division, 0) + 1
        team["rank"] = rank
        team["divisionRank"] = ranks[division]
        team["scheduleStrength"] = round(sum(ratings[g["opponent"]] for g in team["games"]) / len(team["games"]), 6)
    fixtures = []
    for row in rows:
        if int(row["Season"]) == season and int(row["Week"]) == week and row["SeasonType"] == "regular" and not truth(row["Completed"]):
            home, away = row["HomeTeam"], row["AwayTeam"]
            fixtures.append({"id": row["Id"], "home": home, "away": away, "date": row["StartDate"], "neutral": truth(row.get("NeutralSite")), "classification": row.get("HomeClassification", "unknown"), "awayClassification": row.get("AwayClassification", "unknown"), "homeEdge": round(ratings[home] - ratings[away], 2) if home in ratings and away in ratings else None})
    excluded = [r["Id"] for r in rows if int(r["Season"]) == season and int(r["Week"]) < week and r["SeasonType"] == "regular" and truth(r["Completed"]) and (not r["HomePoints"].strip() or not r["AwayPoints"].strip())]
    return {"season": season, "week": week, "throughWeek": week - 1, "gameCount": len(games), "excludedMissingScores": excluded, "latestGameDate": max(g["StartDate"] for g in games), "sourceSha256": source_hash, "model": {"marginCap": 28, "winnerBonus": BONUS, "priorWeight": PRIOR_WEIGHT, "priorSeason": season - 1, "homeAdvantage": 0}, "teams": ordered, "fixtures": sorted(fixtures, key=lambda g: (g["date"], g["id"]))}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True, help="Publication week; includes completed games through week minus one")
    parser.add_argument("--priors", type=Path, help="Prior-season CSV with Team and MasseyRating")
    parser.add_argument("--rebuild-2025-priors", action="store_true", help="Regenerate 2025 priors from archived data with symmetric margin caps")
    parser.add_argument("--site", type=Path, default=ROOT.parents[1] / "tanner49.github.io" / "tanner-ratings" / "data")
    args = parser.parse_args()
    if args.week < 2:
        parser.error("Publication week must be at least 2")
    if args.rebuild_2025_priors:
        archive = ROOT / "archive" / "2025"
        old_priors = {r["Team"]: float(r["MasseyRating"]) for r in read_csv(archive / "MasseyRatings_2024.csv")}
        corrected = solve(select_games(read_csv(archive / "cfbweek15.csv"), 2025, 16), old_priors, prior_weight=HISTORICAL_2025_PRIOR_WEIGHT)
        prior_path = ROOT / "data" / "generated" / "priors-2025.csv"
        prior_path.parent.mkdir(parents=True, exist_ok=True)
        with prior_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Team", "MasseyRating"])
            writer.writerows(sorted(corrected.items(), key=lambda pair: -pair[1]))
    prior_path = args.priors or ROOT / "data" / "generated" / f"priors-{args.season - 1}.csv"
    priors = {r["Team"]: float(r["MasseyRating"]) for r in read_csv(prior_path)}
    if not all(math.isfinite(value) for value in priors.values()):
        raise ValueError("Prior ratings must be finite")
    snapshot = build_snapshot(read_csv(args.input), args.season, args.week, priors, hashlib.sha256(args.input.read_bytes()).hexdigest())
    snapshot["priorSha256"] = hashlib.sha256(prior_path.read_bytes()).hexdigest()
    filename = f"{args.season}/week-{args.week:02}.json"
    # An existing published week is immutable unless the content is identical.
    destinations = [ROOT / "data" / "generated" / filename, args.site / filename]
    for path in destinations:
        if path.exists() and json.loads(path.read_text(encoding="utf-8")) != snapshot:
            raise ValueError(f"Snapshot already exists with different content: {path}. Archive/remove it explicitly before correcting a published week.")
    for path in destinations:
        write_json(path, snapshot)
    csv_path = destinations[0].with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["rank", "divisionRank", "team", "classification", "conference", "rating", "wins", "losses", "ties", "scheduleStrength"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(snapshot["teams"])
    args.site.mkdir(parents=True, exist_ok=True)
    (args.site / filename).with_suffix(".csv").write_bytes(csv_path.read_bytes())
    manifest = []
    for path in args.site.glob("*/week-*.json"):
        saved = json.loads(path.read_text(encoding="utf-8"))
        manifest.append({"season": saved["season"], "week": saved["week"], "path": path.relative_to(args.site).as_posix()})
    write_json(args.site / "index.json", {"snapshots": sorted(manifest, key=lambda s: (s["season"], s["week"]))})
    print(f"Published {args.season} Week {args.week}: {snapshot['gameCount']} games, {len(snapshot['teams'])} teams")
    if snapshot["excludedMissingScores"]:
        print("Excluded completed games without scores: " + ", ".join(snapshot["excludedMissingScores"]))
    for team in [t for t in snapshot["teams"] if t["classification"] == "fbs"][:10]:
        print(f"{team['divisionRank']:2}. {team['team']:25} {team['rating']:8.3f}")


if __name__ == "__main__":
    main()
