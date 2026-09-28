"""Private, fixed-rule weekly ATS backtest. No website output or Git operations."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import collections
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
from production_ratings import read_csv, solve, halftime_margin, game_target, truth

DATA = ROOT / 'data'
OUT = ROOT / 'results'
MODELS = ('halftime1.25', 'cap28')

def stamp(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_games(year):
    result = []
    seen = set()
    for row in read_csv(DATA / f'games_{year}.csv'):
        if not truth(row['Completed']) or not row['HomePoints'] or not row['AwayPoints']:
            continue
        assert int(row['Season']) == year
        assert row['Id'] not in seen
        seen.add(row['Id'])
        for side in ('Home', 'Away'):
            score = float(row[side+'Points'])
            assert math.isfinite(score) and score >= 0 and score.is_integer()
            row[side+'Points'] = int(score)
        result.append(row)
    return sorted(result, key=lambda r: (r['StartDate'], r['Id']))

def fbs(g):
    return 'fbs' in (g['HomeClassification'], g['AwayClassification'])

def period(g):
    if g['SeasonType'] == 'regular':
        return f"regular-{int(g['Week']):02}"
    day = stamp(g['StartDate']).date()
    monday = day - timedelta(days=day.weekday())
    return 'postseason-' + monday.isoformat()

def prior_weight(label):
    return max(0, 1 - .25*(int(label.split('-')[1])-4)) if label.startswith('regular') else 0

def training_window(games, label):
    cutoff = min(stamp(g['StartDate']) for g in games if period(g)==label)
    train = [g for g in games if stamp(g['StartDate'])+timedelta(hours=12)<cutoff and period(g)!=label]
    return cutoff, train

def half_round(value):
    value = round(value, 2)
    return math.copysign(math.floor(abs(value)*2+.5)/2, value)

def grade(prediction, market, actual):
    if prediction == market:
        return 'PASS'
    if actual == market:
        return 'P'
    return 'W' if (prediction-market)*(actual-market) > 0 else 'L'

def get_line(g):
    """Use provider 58 only. Separate explicit close from archived-current fallback."""
    path = DATA / 'odds' / g['Season'] / (g['Id']+'.json')
    if not path.exists():
        return {'lineStatus': 'missing_response'}
    items = json.loads(path.read_text(encoding='utf-8')).get('items', [])
    item = next((x for x in items if str(x.get('provider', {}).get('id')) == '58'), None)
    if item is None:
        return {'lineStatus': 'no_provider_58'}
    for side in ('Home', 'Away'):
        reference = item.get(side.lower()+'TeamOdds', {}).get('team', {}).get('$ref', '')
        match = re.search(r'/teams/(\d+)', reference)
        if not match or match.group(1) != str(g[side+'Id']):
            return {'lineStatus': 'team_id_mismatch'}
    base = {'provider': item['provider']['name'], 'providerId': '58', 'oddsSha256': digest(path)}
    reason = ''
    for basis in ('close', 'current'):
        try:
            home = float(item['homeTeamOdds'][basis]['pointSpread']['american'])
            away = float(item['awayTeamOdds'][basis]['pointSpread']['american'])
            # American prices (100+) sometimes wrongly populate pointSpread.
            assert math.isfinite(home) and home == -away and abs(home) < 100
            assert (home*2).is_integer()
        except (KeyError, ValueError, TypeError, AssertionError):
            if basis == 'close':
                reason = 'missing_or_malformed_close'
            continue
        return {**base, 'lineStatus': 'explicit_close' if basis == 'close' else 'archived_current',
                'lineCaveat': reason, 'homeSpread': home, 'marketHomeMargin': -home}
    return {**base, 'lineStatus': 'no_valid_spread'}

def bootstrap_2022(current):
    """2022-only cap28 bootstrap; no quarter data in the schedule archive."""
    with gzip.open(DATA / 'cfb_schedules_2022.csv.gz', 'rt', encoding='utf-8') as f:
        raw = list(csv.DictReader(f))
    games = []
    id_names = {g[s+'Id']:g[s+'Team'] for g in current for s in ('Home', 'Away')}
    names_ids = {}
    first2023 = min(stamp(g['StartDate']) for g in current)
    for r in raw:
        if not truth(r['completed']) or not r['home_points'] or not r['away_points']:
            continue
        assert stamp(r['start_date']) + timedelta(hours=12) < first2023
        g = {}
        for side in ('Home', 'Away'):
            key = side.lower()
            ident = r[key+'_id']
            name = id_names.get(ident, r[key+'_team'])
            names_ids[name] = ident
            g[side+'Team'] = name
            g[side+'Points'] = int(float(r[key+'_points']))
        games.append(g)
    ratings = solve(games, {}, prior_weight=0, margin_model='cap28')
    write_csv(OUT / 'prior-2023.csv', [{'id':names_ids[n], 'team':n, 'rating':v} for n,v in ratings.items()])
    return {names_ids[n]:v for n,v in ratings.items()}, {'games':len(games), 'model':'2022 cap28; no prior; no quarter scores available',
        'sourceSha256':digest(DATA / 'cfb_schedules_2022.csv.gz')}

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

def summary(rows, model='halftime1.25', raw=False):
    field = model + ('RawResult' if raw else 'Result')
    counts = collections.Counter(r[field] for r in rows)
    w,l,p = (counts[k] for k in ('W','L','P'))
    n = w+l
    rate = w/n if n else None
    z = 1.95996398454
    if n:
        center = (rate + z*z/(2*n))/(1+z*z/n)
        half = z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
        interval = [center-half,center+half]
    else:
        interval = None
    profit = 100*w-110*l
    risk = 110*(w+l+p)
    return {'games':len(rows), 'wins':w,'losses':l,'pushes':p,'passes':counts['PASS'],
            'winRate':rate,'profit':profit,'risked':risk,'ROI':profit/risk if risk else None,
            'winRateWilson95':interval}

def main():
    OUT.mkdir(exist_ok=True)
    seasons = {y:load_games(y) for y in (2023,2024,2025)}
    prior_by_id, bootstrap = bootstrap_2022(seasons[2023])
    predictions = []
    audits = []
    for year, games in seasons.items():
        names_ids = {g[s+'Team']:g[s+'Id'] for g in games for s in ('Home','Away')}
        priors = {n:prior_by_id[i] for n,i in names_ids.items() if i in prior_by_id}
        candidates = [g for g in games if fbs(g) and (g['SeasonType']!='regular' or int(g['Week'])>=4)]
        groups = collections.defaultdict(list)
        for g in candidates:
            groups[period(g)].append(g)
        for label, fixtures in sorted(groups.items(), key=lambda item:min(g['StartDate'] for g in item[1])):
            # Freeze before ANY game in this period, including lower divisions.
            cutoff, train = training_window(games, label)
            assert train and not ({g['Id'] for g in train}&{g['Id'] for g in fixtures})
            assert max(stamp(g['StartDate'])+timedelta(hours=12) for g in train)<cutoff
            weight = prior_weight(label)
            fits = {m:solve(train,priors,prior_weight=weight,margin_model=m) for m in MODELS}
            audit = {'season':year,'period':label,'cutoff':cutoff.isoformat(),'priorWeight':weight,
                     'trainCount':len(train),'trainIds':[g['Id'] for g in train],
                     'latestTrainKickoff':max(g['StartDate'] for g in train),
                     'quarterCoverage':sum(halftime_margin(g) is not None for g in train),
                     'halftimeAdjustedGames':sum(game_target(g,'halftime1.25')!=game_target(g,'cap28') for g in train),
                     'fixtures':[g['Id'] for g in fixtures],
                     'excludedNotSafelyFinished':[g['Id'] for g in games if stamp(g['StartDate'])<cutoff<=stamp(g['StartDate'])+timedelta(hours=12)]}
            audits.append(audit)
            write_csv(OUT / 'weekly-ratings' / f'{year}-{label}.csv',
                      [{'team':n,**{m:r[n] for m,r in fits.items()}} for n in sorted(fits[MODELS[0]])])
            print(year,label,len(train),'prior',weight,flush=True)
            for g in fixtures:
                line = get_line(g)
                home,away = g['HomeTeam'],g['AwayTeam']
                row = {'season':year,'period':label,'id':g['Id'],'date':g['StartDate'],'home':home,'away':away,
                       'bothFBS':g['HomeClassification']==g['AwayClassification']=='fbs',
                       'neutral':truth(g['NeutralSite']),'homeScore':g['HomePoints'],'awayScore':g['AwayPoints'],
                       'actualHomeMargin':g['HomePoints']-g['AwayPoints'],'priorWeight':weight,**line}
                row['modelAvailable'] = all(home in r and away in r for r in fits.values())
                if row['modelAvailable']:
                    for m,ratings in fits.items():
                        raw = ratings[home]-ratings[away]+(0 if row['neutral'] else 3)
                        pred = half_round(raw)
                        row[m+'Raw']=raw
                        row[m+'Prediction']=pred
                        if 'marketHomeMargin' in line:
                            market=line['marketHomeMargin']
                            row[m+'Result']=grade(pred,market,row['actualHomeMargin'])
                            row[m+'RawResult']=grade(raw,market,row['actualHomeMargin'])
                            row[m+'Pick']='PASS' if pred==market else home if pred>market else away
                            row[m+'Profit']={'W':100,'L':-110,'P':0,'PASS':0}[row[m+'Result']]
                predictions.append(row)
        # Bootstrap next season from this season's final available results only.
        final = solve(games,{},prior_weight=0,margin_model='halftime1.25')
        prior_by_id = {names_ids[n]:v for n,v in final.items()}
        write_csv(OUT / f'prior-{year+1}.csv',[{'id':names_ids[n],'team':n,'rating':v} for n,v in final.items()])
        if year<2025:
            assert max(stamp(g['StartDate'])+timedelta(hours=12) for g in games)<min(stamp(g['StartDate']) for g in seasons[year+1])
    predictions.sort(key=lambda r:(r['date'],r['id']))
    write_csv(OUT / 'game-by-game.csv',predictions)
    (OUT / 'weekly-audit.json').write_text(json.dumps(audits,indent=2)+'\n')
    report={'rules':{'model':'halftime1.25','winnerBonus':2.75,'homeAdvantage':3,'riskPerBet':110,'winProfit':100,
                     'firstBetWeek':4,'priorWeights':{'4':1,'5':.75,'6':.5,'7':.25,'8+':0},
                     'bookProviderId':'58','rounding':'stored 2 decimals, displayed nearest half; ties away from zero',
                     'zeroEdge':'pass','scope':'completed supplied games involving at least one FBS team',
                     'cutoff':'before first kickoff of each regular week / postseason Monday-Sunday period; require 12h since training kickoff'},
            'bootstrap':bootstrap,'inputHashes':{f'games_{y}.csv':digest(DATA/f'games_{y}.csv') for y in seasons},
            'productionCodeSha256':digest(ROOT/'production_ratings.py'),
            'coverage':{str(y):dict(collections.Counter(r['lineStatus'] for r in predictions if r['season']==y)) for y in seasons},
            'noModel':[r['id'] for r in predictions if not r['modelAvailable']],
            'lastCompletedGame':{str(y):max(g['StartDate'] for g in games) for y,games in seasons.items()},'samples':{}}
    for sample,statuses in [('explicitClose',{'explicit_close'}),('includingArchivedCurrent',{'explicit_close','archived_current'})]:
        rows=[r for r in predictions if r['lineStatus'] in statuses and r['modelAvailable']]
        report['samples'][sample]={}
        selections={'all':rows,**{str(y):[r for r in rows if r['season']==y] for y in seasons},
                    'FBSvsFBS':[r for r in rows if r['bothFBS']], 'FBSvsOther':[r for r in rows if not r['bothFBS']],
                    'regularOnly':[r for r in rows if r['period'].startswith('regular')],
                    'postseasonOnly':[r for r in rows if r['period'].startswith('postseason')]}
        for name,selected in selections.items():
            report['samples'][sample][name]={m:summary(selected,m) for m in MODELS}
            report['samples'][sample][name]['halftimeUnrounded']=summary(selected,raw=True)
        weekly=[]
        running=peak=drawdown=0
        for row in rows:
            running+=row['halftime1.25Profit'];peak=max(peak,running);drawdown=max(drawdown,peak-running)
        report['samples'][sample]['maxDrawdown']=drawdown
        for audit in audits:
            rs=[r for r in rows if r['season']==audit['season'] and r['period']==audit['period']]
            weekly.append({'season':audit['season'],'period':audit['period'],**summary(rs)})
        write_csv(OUT / f'weekly-{sample}.csv',weekly)
    (OUT / 'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['samples']['explicitClose'],indent=2))

if __name__=='__main__':
    main()
