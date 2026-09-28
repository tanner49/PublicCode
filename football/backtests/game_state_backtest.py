"""Prespecified game-state hypotheses, evaluated with unchanged walk-forward windows."""
import grid_search as grid
from grid_search import *

STATE_OUT=ROOT/'game-state-results'
RULES=[('C00','baseline'),('OT','baseline_ot'),('CAP','cap_ot'),('SOFT','soft_ot'),
       ('STATE_CAP','state_cap_ot'),('STATE_SOFT','state_soft_ot')]

def periods(g):
    result=[]
    for side in ('Home','Away'):
        try:q=[int(x.strip()) for x in g.get(side+'LineScores','').split(',')]
        except (ValueError,TypeError):return None
        if len(q)<4 or min(q)<0 or sum(q)!=g[side+'Points']:return None
        result.append(q)
    return result

def quarter_weight(lead,q):
    # q is zero-based; opening quarter always fully counted.
    if q==0:return 1.
    threshold={1:28,2:21,3:14}[q]
    excess=max(0,abs(lead)-threshold)
    return 1/(1+(excess/14)**2)

def soft_cap(value):
    return math.copysign(min(abs(value),28)+.25*max(0,abs(value)-28),value) if value else 0.

def target(g,rule):
    final=g['HomePoints']-g['AwayPoints']
    bonus=math.copysign(2.75,final) if final else 0.
    if rule=='baseline':return game_target(g,'halftime1.25')
    qs=periods(g)
    if qs is None:return game_target(g,'cap28')
    home,away=qs;reg=sum(home[:4])-sum(away[:4])
    if len(home)>4 or len(away)>4:
        # Do not interpret malformed period arrays as genuine overtime.
        if reg!=0:return game_target(g,'cap28')
        return bonus
    if rule=='baseline_ot':return game_target(g,'halftime1.25')
    if rule=='cap_ot':return math.copysign(min(abs(reg),28),reg)+bonus if reg else bonus
    if rule=='soft_ot':return soft_cap(reg)+bonus
    lead=0;adjusted=0.
    for q in range(4):
        margin=home[q]-away[q]
        adjusted+=quarter_weight(lead,q)*margin
        lead+=margin
    if rule=='state_cap_ot':return (math.copysign(min(abs(adjusted),28),adjusted) if adjusted else 0.)+bonus
    if rule=='state_soft_ot':return soft_cap(adjusted)+bonus
    raise ValueError(rule)

def target_vectors(games,c):return np.array([target(g,c['marginRule']) for g in games])

def main():
    STATE_OUT.mkdir(exist_ok=True)
    for sub in ['bets','weekly-ratings']:(STATE_OUT/sub).mkdir(exist_ok=True)
    configs=[dict(id=ident,stage='hypothesis',marginRule=rule,**BASE) for ident,rule in RULES]
    plan={'primary':'STATE_SOFT','controls':configs,
          'quarterWeights':'Q1=1; Q2/Q3/Q4 thresholds 28/21/14; weight=1/(1+(max(0,abs(actual entering lead)-threshold)/14)^2)',
          'softCap':'signed(min(abs(adjustedMargin),28)+0.25*max(0,abs(adjustedMargin)-28)); then add actual winner bonus 2.75',
          'overtime':'valid extra-period arrays with regulation tie: target actual winner bonus only; no overtime margin credit',
          'badQuarters':'cap28 fallback; actual score determines subsequent weights; no future quarter affects an earlier weight',
          'allOtherRules':'original baseline +3 home, regular W4 start bets, prior W4=1 / W5=.75 / W6=.5 / W7=.25 / W8+=0; fixed 2022 bootstrap and candidate-specific prior-year finals',
          'sample':'same 1858 explicit-close matches, 47 forecast periods, 2023/2024 complete supplied seasons and 2025 through W14; hypothetical -110',
          'optimization':'none; primary and controls fixed before evaluation; previously inspected seasons are not a new holdout',
          'hashes':{str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'game_state_backtest.py',ROOT/'grid_search.py',OUT/'weekly-audit.json',OUT/'game-by-game.csv',OUT/'prior-2023.csv',*[DATA/f'games_{y}.csv' for y in (2023,2024,2025)]]}}
    (STATE_OUT/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    audit=[]
    for year in (2023,2024,2025):
        for g in load_games(year):
            qs=periods(g)
            item={'season':year,'id':g['Id'],'home':g['HomeTeam'],'away':g['AwayTeam'],
                  'fbs':fbs(g),'quarterDataValid':qs is not None,
                  'overtime':bool(qs and (len(qs[0])>4 or len(qs[1])>4) and sum(qs[0][:4])==sum(qs[1][:4])),
                  'finalMargin':g['HomePoints']-g['AwayPoints']}
            item.update({ident:target(g,rule) for ident,rule in RULES})
            audit.append(item)
    write_csv(STATE_OUT/'game-targets.csv',audit)
    grid.SEARCH=STATE_OUT;grid.targets=target_vectors
    board=grid.evaluate(configs,'hypothesis')
    write_csv(STATE_OUT/'leaderboard.csv',board)
    (STATE_OUT/'leaderboard.json').write_text(json.dumps(board,indent=2)+'\n')
    print(json.dumps(board,indent=2))

if __name__=='__main__':main()
