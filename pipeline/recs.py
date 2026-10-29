"""v4 stage C: per-person + group recommendations, with Yelp stars as an after-the-fact check only.
Picks each person's scorer from held-out validation (best Spearman that clears the null); otherwise flags low confidence."""
import os, json, re, sys, itertools
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
import numpy as np, pandas as pd
from scipy.stats import rankdata
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'; OCR = f'{DATA}/lists'
val = json.load(open(f'{OUT}/validation_v4.json'))
RST = pd.read_csv(f'{D}/restaurants.csv').set_index('k')
MAIN = json.load(open(f'{OUT}/model_summary.json'))['main']
METHOD_KEY = {'cluster': f'{MAIN}|cluster_fcm', 'knn': f'{MAIN}|knn', 'ridge_aspects': 'ridge_aspects', 'ridge_cuisine_rel': 'ridge_aspects_cuisine_relative', 'ridge_aspects_talk': 'ridge_aspects+talk'}
people = sorted(f[5:-4] for f in os.listdir(OUT) if f.startswith('pred_'))
choice, P = {}, {}
for who in people:
    null = val[f'null|{who}']
    scored = {m: val[f'{k}|{who}'] for m, k in METHOD_KEY.items() if f'{k}|{who}' in val}
    m_best = max(scored, key=lambda m: scored[m]['spearman'])
    ok = scored[m_best]['spearman'] > null['spearman_95'] and scored[m_best]['auc_top3'] > null['auc_95']
    choice[who] = dict(method=m_best, held_out=scored[m_best], beats_null=bool(ok))
    p = pd.read_csv(f'{OUT}/pred_{who}.csv', index_col='k')
    s = p[m_best]; pr_ = (rankdata(s) - 0.5) / len(s)
    # a person's own rating replaces the prediction for places they have been to
    P[who] = pd.DataFrame({'score': s, 'pct_rank': np.where(p.rated_pct.notna(), p.rated_pct, pr_), 'rated': p.rated_pct.notna()}, index=p.index)
print(json.dumps(choice, indent=1))

# Yelp stars and review count from the search-result card of the matched listing (check only)
m4 = json.load(open(f'{OCR}/m4_full.json')); slugs = json.load(open(f'{OCR}/final_slugs.json'))
crowd = {}
for k, slug in slugs.items():
    for c in (m4.get(k) or {}).get('cands', []):
        if c['slug'] == slug:
            mm = re.search(re.escape(c['title']) + r'\s*([\d.]+)\s*\((\d[\d,]*) reviews?\)', c['ctx'])
            if mm: crowd[k] = (float(mm.group(1)), int(mm.group(2).replace(',', '')))
            break
RST['yelp_stars'] = pd.Series({k: v[0] for k, v in crowd.items()}); RST['yelp_reviews'] = pd.Series({k: v[1] for k, v in crowd.items()})

RULES = {
    'average': lambda M: M.mean(axis=1),
    'least_misery': lambda M: M.min(axis=1),
    'trimmed_average': lambda M: (M.sum(axis=1) - M.min(axis=1)) / max(M.shape[1] - 1, 1) if M.shape[1] > 2 else M.mean(axis=1),
    'average_without_misery': lambda M: M.mean(axis=1).where(M.min(axis=1) >= 0.35, -1),
    'multiplicative': lambda M: M.prod(axis=1),
    'borda': lambda M: M.rank().sum(axis=1),
}
def group_recs(group, rule='average', top=15, keep_partial=True):
    idx = P[group[0]].index
    M = pd.DataFrame({w: P[w].pct_rank for w in group}).loc[idx]
    rated = pd.DataFrame({w: P[w].rated for w in group}).loc[idx]
    cand = ~rated.all(axis=1) if keep_partial else ~rated.any(axis=1)
    g = RULES[rule](M)[cand]
    out = pd.DataFrame({'group_score': g}).join(M.add_suffix('_pct')).join(rated.add_suffix('_rated'))
    out['spread'] = M.loc[out.index].max(axis=1) - M.loc[out.index].min(axis=1)
    out = out.join(RST[['name', 'family', 'price', 'yelp_stars', 'yelp_reviews']])
    return out.sort_values('group_score', ascending=False).head(top)

res = {}
for n in range(1, len(people) + 1):
    for group in itertools.combinations(people, n):
        gid = '+'.join(group)
        for rule in (['average'] if n == 1 else RULES):
            r = group_recs(list(group), rule, keep_partial=(n > 1))
            r.round(3).to_csv(f'{OUT}/recs_{gid}_{rule}.csv')
            res[f'{gid}|{rule}'] = r.name.tolist()[:10]
json.dump(dict(choice=choice, recs=res), open(f'{OUT}/recs_summary.json', 'w'), indent=1)
for k, v in res.items(): print(k, '->', v[:6])
# crowd check: do top recs have unusually low Yelp stars?
allstars = RST.yelp_stars.dropna()
for k in [k for k in res if k.endswith('|average')]:
    gid = k.split('|')[0]; r = pd.read_csv(f'{OUT}/recs_{gid}_average.csv')
    print('crowd check', gid, 'mean Yelp stars of top 15:', round(r.yelp_stars.mean(), 2), 'vs pool', round(allstars.mean(), 2),
          '| below 3.5:', r.loc[r.yelp_stars < 3.5, 'name'].tolist())
