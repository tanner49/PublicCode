"""Recompute historical trend ranks under the selected snapshot's scoring rule."""
import hashlib
import json
from pathlib import Path

from ratings import ROOT, build_snapshot, read_csv, write_json


def comparison_history(current, earlier, source_root=ROOT):
    prior_path = source_root / 'data/generated' / f"priors-{current['season']-1}.csv"
    prior_hash = hashlib.sha256(prior_path.read_bytes()).hexdigest()
    if prior_hash != current['priorSha256']:
        raise ValueError('Comparison prior does not match selected snapshot')
    priors = {r['Team']: float(r['MasseyRating']) for r in read_csv(prior_path)}
    result = []
    for old in sorted(earlier, key=lambda s:s['week']):
        if old['season'] != current['season'] or old['week'] >= current['week']:
            raise ValueError('Comparison history must precede selected week in the same season')
        source = source_root / 'data/raw' / str(old['season']) / f"week-{old['week']:02}.csv"
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        if source_hash != old['sourceSha256']:
            raise ValueError('Historical export differs from published source')
        rebuilt = build_snapshot(read_csv(source), old['season'], old['week'], priors, source_hash,
                                 prior_weight=old['model']['priorWeight'],
                                 margin_model=current['model'].get('marginModel','cap28'))
        old_ids = {g['id'] for t in old['teams'] for g in t['games']}
        rebuilt_ids = {g['id'] for t in rebuilt['teams'] for g in t['games']}
        if old_ids != rebuilt_ids:
            raise ValueError('Comparison must use exactly the historical game set')
        result.append({'season':old['season'],'week':old['week'], 'sourceSha256':source_hash,
                       'priorSha256':prior_hash,'model':rebuilt['model'],
                       'teams':[{k:t[k] for k in ('team','classification','rank','divisionRank','rating')} for t in rebuilt['teams']]})
    return {'season':current['season'],'week':current['week'],
            'basis':'Selected week scoring rule; each historical week retains its original games and prior weight.',
            'history':result}


def publish_comparison_histories(data_directory):
    index_path = data_directory / 'index.json'
    manifest = json.loads(index_path.read_text(encoding='utf-8'))
    saved = [(entry,json.loads((data_directory/entry['path']).read_text(encoding='utf-8'))) for entry in manifest['snapshots']]
    for entry,current in saved:
        earlier = [s for _,s in saved if s['season']==current['season'] and s['week']<current['week']]
        if not earlier:
            continue
        relative = f"comparisons/{current['season']}/week-{current['week']:02}.json"
        write_json(data_directory/relative,comparison_history(current,earlier))
        entry['comparisonPath'] = relative
    write_json(index_path,manifest)


if __name__=='__main__':
    publish_comparison_histories(ROOT.parents[1]/'tanner49.github.io/tanner-ratings/data')
