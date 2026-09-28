"""Describe the existing search; no new fitting or parameter selection."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter

ROOT=Path(__file__).resolve().parent/'grid-results'
rows=json.loads((ROOT/'leaderboard.json').read_text())
baseline=next(r for r in rows if r['id']=='C00')
plt.rcParams['text.parse_math']=False
fig,axes=plt.subplots(1,2,figsize=(12,5.4),sharey=True)
bins=np.arange(-6,4.01,.5)
for ax,key,title in zip(axes,['ROI','ROI2025'],['All three seasons pooled','2025 only (through Week 14)']):
    coarse=[100*r[key] for r in rows if r['stage']=='coarse']
    refine=[100*r[key] for r in rows if r['stage']=='refine']
    values=coarse+refine
    ax.hist([coarse,refine],bins=bins,stacked=True,color=['#4f7895','#d4a253'],
            edgecolor='white',linewidth=.8,label=['25 broad candidates','10 local refinements'])
    ax.axvline(0,color='#333333',lw=1.5,label='Break-even')
    ax.axvline(100*baseline[key],color='#a43b44',ls='--',lw=1.7,label='Current model')
    ax.set_title(title,fontsize=13,pad=12)
    ax.set_xlabel('Return on total amount staked')
    ax.set_xlim(-6,4)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100,decimals=0))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.spines[['top','right']].set_visible(False)
    ax.text(.97,.96,f'{sum(v>0 for v in values)}/35 profitable\nMedian: {np.median(values):+.2f}%',
            transform=ax.transAxes,ha='right',va='top',fontsize=11)
    ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axes[0].set_ylabel('Number of model configurations')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.09),ncol=4,frameon=False)
fig.suptitle('ROI across all 35 tested configurations',fontsize=17,weight='bold',y=.98)
fig.text(.5,.025,'$110 risk / $100 win | 0.5-percentage-point bins | Same games reused across models; configurations are not independent trials.',
         ha='center',fontsize=9,color='#444444')
fig.tight_layout(rect=(0,.18,1,.93))
fig.savefig(ROOT/'roi-histogram.png',dpi=180)
fig.savefig(ROOT/'roi-histogram.svg')
print(ROOT/'roi-histogram.png')
