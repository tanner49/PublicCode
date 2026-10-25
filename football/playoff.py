"""Project conference champions, select a rules-aware CFP field, and draw its bracket."""
import hashlib
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from ratings import truth, read_csv

POWER = ('ACC', 'Big Ten', 'Big 12', 'SEC')
GROUP = ('American Athletic', 'Conference USA', 'Mid-American', 'Mountain West', 'Pac-12', 'Sun Belt')
RULES_URL = 'https://collegefootballplayoff.com/sports/2024/5/29/12-team-format'

def order_teams(teams):
    return sorted(teams, key=lambda t: (-t['rating'], t['team']))

def project_champions(snapshot, schedule):
    teams = {t['team']: t for t in snapshot['teams'] if t['classification'] == 'fbs'}
    table = {name: dict(team=name, wins=0, losses=0, ties=0) for name in teams}
    results = []
    for g in schedule:
        if int(g['Season']) != snapshot['season'] or g['SeasonType'] != 'regular' or not truth(g.get('ConferenceGame')):
            continue
        home, away = g['HomeTeam'], g['AwayTeam']
        if home not in teams or away not in teams: continue
        conference = teams[home]['conference']
        if conference not in POWER or teams[away]['conference'] != conference: continue
        actual = int(g['Week']) < snapshot['week'] and truth(g['Completed']) and g['HomePoints'].strip() and g['AwayPoints'].strip()
        if actual:
            margin = int(g['HomePoints']) - int(g['AwayPoints'])
        else:
            margin = teams[home]['rating'] - teams[away]['rating'] + (0 if truth(g.get('NeutralSite')) else 3)
            if margin == 0: margin = 1 if order_teams([teams[home], teams[away]])[0]['team'] == home else -1
        winner = home if margin > 0 else away if margin < 0 else None
        table[home]['wins' if margin > 0 else 'losses' if margin < 0 else 'ties'] += 1
        table[away]['wins' if margin < 0 else 'losses' if margin > 0 else 'ties'] += 1
        results.append(dict(id=g['Id'], conference=conference, home=home, away=away, winner=winner, projected=not bool(actual), homeMargin=margin))
    champions = {}
    for conference in POWER:
        members = [t for t in teams.values() if t['conference'] == conference]
        if len(members) < 2: raise ValueError(f'Missing conference membership: {conference}')
        groups = defaultdict(list)
        for t in members:
            r = table[t['team']]; played = r['wins'] + r['losses'] + r['ties']
            if not played: raise ValueError(f'No conference schedule for {t["team"]}')
            groups[Fraction(2*r['wins'] + r['ties'], 2*played)].append(t)
        ordered = []; ties = []
        for pct, tied in sorted(groups.items(), reverse=True):
            head_to_head = False
            if len(tied) == 2:
                pair = {t['team'] for t in tied}
                meetings = [r for r in results if {r['home'],r['away']} == pair and r['winner']]
                if len(meetings) == 1:
                    tied = sorted(tied, key=lambda t: t['team'] != meetings[0]['winner']); head_to_head = True
                else: tied = order_teams(tied)
            else: tied = order_teams(tied)
            if len(tied) > 1: ties.append(dict(teams=[t['team'] for t in tied],method='head-to-head' if head_to_head else 'model rating'))
            ordered.extend(tied)
        finalists = ordered[:2]
        champ = order_teams(finalists)[0] # neutral-field championship, current model strength
        champions[conference] = dict(team=champ['team'],finalists=[t['team'] for t in finalists],standings=[dict(table[t['team']], rating=t['rating']) for t in ordered],tiebreaks=ties)
    return champions, results

def select_field(snapshot, champions):
    ranked = order_teams(t for t in snapshot['teams'] if t['classification'] == 'fbs')
    byname = {t['team']: t for t in ranked}; rank = {t['team']: i+1 for i,t in enumerate(ranked)}
    bids = {champions[c]['team']: f'{c} champ' for c in POWER}
    group = next((t for t in ranked if t['conference'] in GROUP), None)
    if group is None: raise ValueError('Missing Group of Six teams')
    bids[group['team']] = 'Group of Six bid'
    if 'Notre Dame' in rank and rank['Notre Dame'] <= 12: bids['Notre Dame'] = 'Notre Dame guarantee'
    selected = set(bids)
    for t in ranked:
        if len(selected) == 12: break
        selected.add(t['team'])
    if len(selected) != 12: raise ValueError('A playoff field requires 12 distinct teams')
    return [dict(byname[name], seed=i+1, modelRank=rank[name], bid=bids.get(name,'At-large')) for i,name in enumerate(sorted(selected,key=lambda n:rank[n]))]

def build_playoff(snapshot, schedule):
    if snapshot['season'] != 2026: raise ValueError('Verify CFP rules before enabling another season')
    champions, results = project_champions(snapshot, schedule)
    field = select_field(snapshot, champions)
    return dict(season=snapshot['season'],week=snapshot['week'],throughWeek=snapshot['throughWeek'],field=field,conferenceChampions=champions,conferenceResults=results,
        rulesSource=RULES_URL,
        method='Current Prove It ratings stand in for committee rankings. Predict remaining regular-season conference games at current ratings plus 3 home points, neutral zero, keeping completed results through this snapshot. Top two by projected conference winning percentage reach each Power Four title game; two-team ties use head-to-head when available, other ties use model rating (not all official conference tiebreakers). Higher-rated finalist wins a neutral title game. Four Power Four champions and the top-rated Group of Six team receive bids; Notre Dame is protected if model top 12. Fill to 12 by model rating, then seed by rating, with top four byes. Bracket winners use home +3 in round one, neutral thereafter. Ratings are held fixed; not a forecast of committee decisions or updated final-season ratings.')

def render_playoff(snapshot, site, folder):
    from PIL import Image, ImageDraw
    from share_cards import text, logo_badge, INK, PAPER, LIME, ORANGE, MUTED
    raw = Path(__file__).parent/'data/raw'/str(snapshot['season'])/f"week-{snapshot['week']:02}.csv"
    if hashlib.sha256(raw.read_bytes()).hexdigest() != snapshot['sourceSha256']: raise ValueError('Playoff schedule does not match snapshot input')
    audit = build_playoff(snapshot,read_csv(raw));audit['sourceSha256']=snapshot['sourceSha256']
    folder.mkdir(parents=True,exist_ok=True)
    logos = json.loads((site/'logos/index.json').read_text(encoding='utf-8'))
    image=Image.new('RGB',(1200,850),INK);draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,1200,9),fill=LIME)
    text(draw,(42,29),'THE “PROVE IT” RANKINGS',23,LIME,True)
    text(draw,(1158,29),f"{snapshot['season']}  ·  WEEK {snapshot['week']}",25,LIME,True,anchor='rt')
    text(draw,(40,68),'THE PLAYOFF PICTURE.',78,bold=True,width=1115)
    text(draw,(43,157),'Projected conference champs. Automatic bids. A path to the title.',25,MUTED)
    columns=[42,328,614,900];width=258
    for x,label in zip(columns,['FIRST ROUND','QUARTERFINALS','SEMIFINALS','CHAMPIONSHIP']):text(draw,(x,205),label,22,LIME,True)
    field={t['seed']:t for t in audit['field']};rounds=[]
    def winner(a,b,home=False):return a if a['rating']+(3 if home else 0)>=b['rating'] else b
    def box(x,y,a,b,home=False):
        win=winner(a,b,home);draw.rounded_rectangle((x,y-40,x+width,y+40),radius=8,fill='#243c2e')
        for j,t in enumerate([a,b]):
            yy=y-33+j*39;selected=t['team']==win['team'];color=PAPER if selected else MUTED
            text(draw,(x+8,yy+4),t['seed'],24,LIME if selected else MUTED,True)
            logo_badge(image,site,logos,t['team'],x+38,yy,32)
            text(draw,(x+79,yy+2),t['team'],25,color,selected,width=width-87)
        draw.line((x,y+1,x+width,y+1),fill='#334c3b')
        # Thin accent identifies the model's projected advancing team.
        draw.rounded_rectangle((x,y-38 if win is a else y+2,x+3,y-3 if win is a else y+37),radius=1,fill=LIME)
        rounds.append(dict(home=a['team'],away=b['team'],winner=win['team'],neutral=not home))
        return win
    def link(x1,y1,x2,y2):
        mid=(x1+x2)//2;draw.line([(x1,y1),(mid,y1),(mid,y2),(x2,y2)],fill='#69836d',width=2)
    ys=[284,414,544,674]
    # Fixed CFP paths: 8/9 -> 1; 5/12 -> 4; 7/10 -> 2; 6/11 -> 3.
    pairs=[(8,9,1),(5,12,4),(7,10,2),(6,11,3)];first=[];quarters=[]
    for y,(high,low,bye) in zip(ys,pairs):
        text(draw,(columns[0]+width//2,y-56),'HIGHER SEED HOSTS',14,MUTED,anchor='mt')
        first.append(box(columns[0],y,field[high],field[low],True))
        link(columns[0]+width,y,columns[1],y)
        quarters.append(box(columns[1],y,field[bye],first[-1]))
        text(draw,(columns[1]+width//2,y-56),f'SEED {bye} · FIRST-ROUND BYE',14,MUTED,anchor='mt')
    semi_y=[349,609];semis=[]
    for i,y in enumerate(semi_y):
        for q in (2*i,2*i+1):link(columns[1]+width,ys[q],columns[2],y)
        semis.append(box(columns[2],y,quarters[2*i],quarters[2*i+1]))
    final_y=479
    for y in semi_y:link(columns[2]+width,y,columns[3],final_y)
    champion=box(columns[3],final_y,*semis)
    text(draw,(columns[3]+width//2,552),'PROJECTED CHAMPION',17,LIME,True,anchor='mt')
    logo_badge(image,site,logos,champion['team'],columns[3]+97,586,64)
    text(draw,(columns[3]+width//2,667),champion['team'],30,bold=True,width=width,anchor='mt')
    champions=' · '.join(f"{c}: {audit['conferenceChampions'][c]['team']}" for c in POWER)
    text(draw,(42,747),'PROJECTED CHAMPS  '+champions,20,MUTED,width=1116)
    group=next(t for t in audit['field'] if t['bid']=='Group of Six bid')
    text(draw,(42,775),f"GROUP OF SIX  {group['team']} (model #{group['modelRank']})  ·  Highlighted teams advance in our model",20,LIME,width=1116)
    draw.line((42,808,1158,808),fill='#47604e')
    text(draw,(42,824),'COLLEGE FOOTBALL',20,LIME,True)
    text(draw,(1158,824),f"Results through Week {snapshot['throughWeek']} · Model projection",20,PAPER,anchor='rt')
    audit['projectedPlayoffGames']=rounds;audit['projectedChampion']=champion['team']
    image.save(folder/'playoff.png',optimize=True)
    (folder/'playoff.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return audit
