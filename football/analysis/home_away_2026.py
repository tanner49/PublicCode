"""Retrospective home/away margin residuals using one current weekly snapshot."""
import argparse,csv,json,math
from pathlib import Path
import sys
from statistics import mean,median,stdev
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from share_cards import font,text,logo_badge,INK,PAPER,LIME,ORANGE,MUTED

def calculate(snapshot,fbs_only=True):
 teams={t['team']:t for t in snapshot['teams']};result=[];hfa=snapshot['model'].get('homeAdvantage',3)
 for name,t in teams.items():
  if t['classification']!='fbs':continue
  splits={'H':[],'A':[]};games=[]
  for g in t['games']:
   if g['venue'] not in splits:continue
   opp=teams[g['opponent']]
   if fbs_only and opp['classification']!='fbs':continue
   prediction=t['rating']-opp['rating']+(hfa if g['venue']=='H' else -hfa)
   actual=g['scored']-g['allowed'];residual=actual-prediction;splits[g['venue']].append(residual)
   games.append(dict(id=g['id'],opponent=g['opponent'],venue=g['venue'],actualMargin=actual,predictedMargin=prediction,residual=residual))
  if min(map(len,splits.values()))<3:continue
  h,a=mean(splits['H']),mean(splits['A']);se=math.sqrt(stdev(splits['H'])**2/len(splits['H'])+stdev(splits['A'])**2/len(splits['A']))
  result.append(dict(team=name,rating=t['rating'],conference=t['conference'],homeMean=h,awayMean=a,homeGames=len(splits['H']),awayGames=len(splits['A']),homeMinusAway=h-a,homeMedian=median(splits['H']),awayMedian=median(splits['A']),roughGapSE=se,games=games))
 return sorted(result,key=lambda r:(-r['homeMinusAway'],r['team']))

def render(snapshot,rows,site,out,kind):
 image=Image.new('RGB',(1600,1190),INK);d=ImageDraw.Draw(image)
 d.rectangle((0,0,1600,11),fill=LIME)
 text(d,(50,35),'THE “PROVE IT” RANKINGS',29,LIME,True)
 text(d,(1550,35),f"{snapshot['season']} · WEEK {snapshot['week']}",29,LIME,True,anchor='rt')
 title='HOME SWEET HOME.' if kind=='home' else 'ROAD WARRIORS.'
 subtitle='Teams that play better at home—and struggle more on the road.' if kind=='home' else 'Teams that play better on the road than they do at home.'
 text(d,(48,89),title,94,bold=True)
 text(d,(52,194),subtitle,32,MUTED)
 text(d,(52,239),'Average final scoring margin above / below today’s model prediction',27,PAPER)
 logos=json.loads((site/'logos/index.json').read_text(encoding='utf-8'))
 selected=(rows if kind=='home' else list(reversed(rows)))[:10]
 left,right=520,1370;lo,hi=-25,20
 def x(v):return left+(v-lo)/(hi-lo)*(right-left)
 top,bottom=350,1004
 for tick in range(-25,21,5):
  d.line((x(tick),top-8,x(tick),bottom),fill='#59725e' if tick==0 else '#2c4636',width=3 if tick==0 else 1)
  text(d,(x(tick),bottom+12),f'{tick:+}' if tick else '0',23,MUTED,anchor='mt')
 text(d,(1500,300),'HOME EDGE' if kind=='home' else 'AWAY EDGE',22,LIME,True,anchor='mt')
 d.ellipse((530,298,548,316),fill=LIME);text(d,(560,294),'HOME',24,LIME,True)
 d.ellipse((700,298,718,316),fill=ORANGE);text(d,(730,294),'AWAY',24,ORANGE,True)
 for i,r in enumerate(selected):
  yy=367+i*66;d.line((52,yy+45,1548,yy+45),fill='#2c4636')
  text(d,(52,yy-8),f'{i+1:02}',33,MUTED,True)
  logo_badge(image,site,logos,r['team'],104,yy-16,48)
  text(d,(169,yy-14),r['team'],33,bold=True,width=305)
  text(d,(171,yy+23),f"{r['homeGames']} home · {r['awayGames']} away",19,MUTED)
  a,b=x(r['awayMean']),x(r['homeMean']);d.line((a,yy+8,b,yy+8),fill='#6e8667',width=7)
  for point,value,color in [(a,r['awayMean'],ORANGE),(b,r['homeMean'],LIME)]:
   d.ellipse((point-9,yy-1,point+9,yy+17),fill=color)
   offset=-16 if point==min(a,b) else 16;anchor='rm' if offset<0 else 'lm'
   text(d,(point+offset,yy+8),f'{value:+.1f}',22,color,True,anchor=anchor)
  gap=r['homeMinusAway']*(1 if kind=='home' else -1)
  text(d,(1505,yy-4),f'+{gap:.1f}',35,LIME,True,anchor='mt')
 text(d,(52,1064),'FBS opponents only · Minimum 3 games at each venue · Neutral sites excluded',25,MUTED)
 text(d,(52,1103),'Includes the model’s 3-point home advantage. Full final margins; no blowout cap in this comparison.',24,MUTED)
 d.line((50,1140,1550,1140),fill='#47604e')
 text(d,(50,1158),'COLLEGE FOOTBALL',25,LIME,True)
 text(d,(1550,1158),f"Results through Week {snapshot['throughWeek']} · Retrospective venue splits",24,PAPER,anchor='rt')
 image.save(out/f'{kind}-away-gap.png',optimize=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();s=json.loads(args.snapshot.read_text(encoding='utf-8'));out=args.output;out.mkdir(parents=True,exist_ok=True);rows=calculate(s);allrows=calculate(s,False)
 for label,rs in [('fbs-opponents',rows),('all-opponents',allrows)]:
  (out/f'{label}.json').write_text(json.dumps(rs,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
  with (out/f'{label}.csv').open('w',newline='',encoding='utf-8') as f:
   fields=[k for k in rs[0] if k!='games'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rs)
 site=ROOT.parents[1]/'tanner49.github.io/tanner-ratings'
 for kind in ('home','road'):render(s,rows,site,out,kind)
 print('Eligible teams',len(rows));print('Home',[(r['team'],round(r['homeMean'],1),round(r['awayMean'],1),round(r['homeMinusAway'],1)) for r in rows[:5]]);print('Road',[(r['team'],round(r['homeMean'],1),round(r['awayMean'],1),round(-r['homeMinusAway'],1)) for r in reversed(rows[-5:])])
if __name__=='__main__':main()
