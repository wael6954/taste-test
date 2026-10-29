"""Draw the README figures from results/ (aggregates only, no review text). Writes docs/img/*.png."""
import json, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(D)
RES = f'{ROOT}/results'; IMG = f'{ROOT}/docs/img'
os.makedirs(IMG, exist_ok=True)

INK, INK2, INK3, GRID, BAD = '#1d1d1f', '#515154', '#6e6e73', '#e3e3e8', '#b3411a'
COL = {'wael': '#0071e3', 'zed': '#c85a14'}
NAME = {'wael': 'Wael', 'zed': 'Z'}
plt.rcParams.update({'font.family': ['Segoe UI', 'Arial', 'DejaVu Sans'], 'font.size': 10, 'text.color': INK,
                     'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK3, 'ytick.color': INK2,
                     'axes.spines.top': False, 'axes.spines.right': False, 'axes.spines.left': False, 'figure.facecolor': 'white'})

val = json.load(open(f'{RES}/validation/validation_v4.json'))
asp = json.load(open(f'{RES}/taste/aspect_correlations_v4.json'))

# ---------- accuracy vs chance ----------
METHODS = [('Aspects + talk rate (ridge)', 'ridge_aspects+talk'), ('Aspect sentiment (ridge)', 'ridge_aspects'), ('Nearest neighbours', 'how_topics+aspects|knn'),
           ('Clusters (GMM)', 'how_topics+aspects|cluster_gmm'), ('Clusters (fuzzy)', 'how_topics+aspects|cluster_fcm'),
           ('Mean embedding, neighbours', 'mean_embedding|knn'), ('Cuisine average (baseline)', 'baseline_cuisine_mean')]
null95 = {'wael': 0.17, 'zed': 0.199}  # random-guess 95th percentile of the 5x5-fold Spearman, as in the app
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharex=True)
for ax, who in zip(axes, ['wael', 'zed']):
    rows = sorted([(m, val[f'{k}|{who}']['spearman']) for m, k in METHODS], key=lambda r: r[1])
    n = val[f'{METHODS[0][1]}|{who}']['n']
    ys = range(len(rows))
    ax.barh(ys, [r[1] for r in rows], height=.62, color=[COL[who] if r[0].startswith('Aspects +') else '#c7c7cc' for r in rows])
    for y, (m, s) in zip(ys, rows):
        ax.text(s + (.008 if s >= 0 else -.008), y, f'{s:.2f}', va='center', ha='left' if s >= 0 else 'right', fontsize=9, color=INK2, bbox=dict(fc='white', ec='none', pad=1.2), zorder=3)
    ax.set_yticks(list(ys)); ax.set_yticklabels([r[0] for r in rows])
    for t, r in zip(ax.get_yticklabels(), rows):
        if r[0].startswith('Aspects +'): t.set_fontweight('bold'); t.set_color(INK)
    ax.axvline(0, color=INK3, lw=.8)
    ax.axvline(null95[who], color=BAD, lw=1, ls=(0, (4, 3)))
    ax.text(null95[who] + .006, -.9, 'random guessing,\n95th percentile', color=BAD, fontsize=8, va='top', ha='left')
    ax.set_title(f'{NAME[who]}  ·  {n} places', loc='left', fontsize=11, fontweight='bold', color=COL[who], pad=10)
    ax.set_xlim(-.27, .5); ax.set_ylim(-1.8, len(rows) - .4); ax.tick_params(length=0)
    ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
fig.supxlabel('Spearman correlation between predicted and actual rank, on places the model had not seen', fontsize=9, color=INK3, y=.02)
fig.tight_layout(rect=(0, .04, 1, 1))
fig.savefig(f'{IMG}/accuracy.png', dpi=200); plt.close(fig)

# ---------- what moves each person ----------
ANAME = {'flavor': 'Food praised', 'quality': 'Ingredients and quality', 'portions': 'Portions', 'service': 'Service', 'wait': 'Worth the wait',
         'logistics': 'Ordering and logistics', 'value': 'Price and value', 'ambience': 'Atmosphere', 'location': 'Location',
         'occasion': 'Occasions', 'overall': 'Would return', 'menu': 'Menu'}
aspects = list(ANAME)
rows = sorted(aspects, key=lambda a: asp[f'wael|{a}']['plain'][0] + asp[f'zed|{a}']['plain'][0])
fig, ax = plt.subplots(figsize=(8.6, 5.6))
h = .36
for i, a in enumerate(rows):
    for who, dy in (('wael', .2), ('zed', -.2)):
        r, p = asp[f'{who}|{a}']['plain']
        ax.barh(i + dy, r, height=h, color=COL[who], alpha=1 if p < .05 else .3, lw=0)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([ANAME[a] for a in rows])
ax.axvline(0, color=INK3, lw=.8); ax.set_xlim(-.25, .35); ax.tick_params(length=0)
ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
ax.set_xlabel('Correlation between how much reviewers say this and where the place sits on the list', fontsize=9, color=INK3)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=COL['wael'], label='Wael'), Patch(color=COL['zed'], label='Z'), Patch(color=INK3, alpha=.3, label='faded: could be chance (p ≥ 0.05)')],
          loc='lower left', bbox_to_anchor=(0, 1.01), ncol=3, frameon=False, fontsize=9, labelcolor=INK2, handlelength=1.2, borderaxespad=0)
fig.tight_layout()
fig.savefig(f'{IMG}/drivers.png', dpi=200); plt.close(fig)
print('wrote', sorted(os.listdir(IMG)))

# ---------- top new picks for both ----------
import pandas as pd
def dumbbell(ax, labels, a, b, xmin, xmax, ref=None):
    ys = list(range(len(labels)))[::-1]
    for y, u, v in zip(ys, a, b):
        ax.plot([u, v], [y, y], color='#c7c7cc', lw=2, zorder=1, solid_capstyle='round')
    ax.scatter(a, ys, s=46, color=COL['wael'], zorder=2, label='Wael')
    ax.scatter(b, ys, s=46, color=COL['zed'], zorder=2, label='Z')
    ax.set_yticks(ys); ax.set_yticklabels(labels); ax.set_xlim(xmin, xmax); ax.set_ylim(-.7, len(labels) - .3)
    ax.tick_params(length=0); ax.xaxis.grid(True, color=GRID, lw=.6); ax.set_axisbelow(True)
    if ref is not None: ax.axvline(ref, color=INK3, lw=.8, ls=(0, (4, 3)))
    ax.legend(loc='lower left', bbox_to_anchor=(0, 1.01), ncol=2, frameon=False, fontsize=9, labelcolor=INK2, borderaxespad=0, handletextpad=.2)

P = pd.read_csv(f'{RES}/new_places/refrecs_wael+zed_average_without_misery.csv', index_col=0).sort_values('group_score', ascending=False).head(15)
fig, ax = plt.subplots(figsize=(8.6, 5.4))
dumbbell(ax, [t if pd.isna(h) else f'{t}  ·  {h}' for t, h in zip(P.title, P.hood)], P.wael_pct * 100, P.zed_pct * 100, 80, 101)
ax.set_xticks(range(80, 101, 5))
ax.set_xlabel("Model's predicted percentile within each person's own list (100 = their best)", fontsize=9, color=INK3)
fig.tight_layout(); fig.savefig(f'{IMG}/picks.png', dpi=200); plt.close(fig)

# ---------- six kinds of restaurant ----------
KIND = {'c0': 'Popular, worth the wait', 'c1': 'Cheap and basic', 'c2': 'Sit-down: ambience and service', 'c3': 'Flavour-first, slow prep',
        'c4': 'Casual brunch, lunch and dates', 'c5': 'Complaint-heavy'}
C = pd.read_csv(f'{RES}/taste/clusters_v4.csv').assign(avg=lambda d: d.wael + d.zed).sort_values('avg', ascending=False)
fig, ax = plt.subplots(figsize=(8.6, 3.6))
dumbbell(ax, [f'{KIND[c]}  ({n} places)' for c, n in zip(C.cluster, C['size'])], C.wael * 100, C.zed * 100, 35, 75, ref=50)
ax.text(50.4, -.62, 'average place', color=INK3, fontsize=8, va='bottom')
ax.set_xlabel("Average percentile of the places in each group, within each person's own list", fontsize=9, color=INK3)
fig.tight_layout(); fig.savefig(f'{IMG}/kinds.png', dpi=200); plt.close(fig)
print('wrote', sorted(os.listdir(IMG)))
