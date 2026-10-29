"""Reference set: map new restaurants onto the frozen v4 topics, build the same aspect features, and score them
with each person's ridge model (fit on all their rated places). Output per-person and group recommendations.
Inputs: data/ref_meta.json, data/ref_emb_chunk_*.bin, data/ref_sent_chunk_*.bin, data/ref_cand.json (Yelp search cards)."""
import os, json, itertools, warnings; warnings.filterwarnings('ignore')
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
import numpy as np, pandas as pd
from scipy.stats import rankdata
from sklearn.linear_model import RidgeCV
from freeze import assign
import sys
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'; PRE = sys.argv[1] if len(sys.argv) > 1 else 'ref'
meta = json.load(open(f'{DATA}/{PRE}_meta.json')); n = len(meta['sent'])
def chunks(stage, dim):
    order = np.array(meta['order']); C = meta['chunk']; X = np.zeros((n, dim), np.float32)
    for c in range(int(np.ceil(n / C))):
        ids = order[c * C:(c + 1) * C]
        X[ids] = np.fromfile(f'{DATA}/{PRE}_{stage}_chunk_{c}.bin', dtype=np.float32).reshape(len(ids), dim)
    return X
E = chunks('emb', 768); P3 = chunks('sent', 3)
assert np.allclose(np.linalg.norm(E, axis=1), 1, atol=1e-3) and np.allclose(P3.sum(1), 1, atol=1e-3)
places = pd.DataFrame(meta['places']); reviews = pd.DataFrame(meta['reviews'])
S = pd.DataFrame(meta['sent'], columns=['p', 'r', 'text']); S['k'] = places.slug.values[S.p.values]
S['pol'] = np.array(['neg', 'neu', 'pos'])[P3.argmax(1)]; S['sent_score'] = P3[:, 2] - P3[:, 0]
ref = np.load(f'{D}/topic_model_v4/reference.npz')
S['topic'] = assign(E, S.pol.values, ref['emb'].astype(np.float32), ref['topic'], ref['pol'])
T = pd.read_csv(f'{D}/topic_model_v4/topics_v4.csv'); TAG = dict(zip(T.topic_id, T.tag))
S['tag'] = S.topic.map(TAG)
nrev = reviews.groupby('p').size().reindex(range(len(places)), fill_value=0); places['nrev'] = nrev.values
keys = sorted(set(places.slug[places.nrev >= 5]))
S = S[S.k.isin(keys)]
print('reference places with >=5 reviews:', len(keys), '| sentences', len(S), '| assigned share', round((S.topic >= 0).mean(), 3))

# same aspect features as model.py, standardized with the POOL's mean/std so the ridge weights apply unchanged
F = pd.read_csv(f'{OUT}/features_v4.csv', index_col='k')
aspects = [c[4:] for c in F if c.startswith('net_')]
n_all = S.groupby('k').size().reindex(keys)
A = S[S.topic >= 0]
net = pd.DataFrame({a: (A[A.tag == a].groupby('k').sent_score.sum() / (A[A.tag == a].groupby('k').size() + 2)).reindex(keys).fillna(0) for a in aspects})
talk = pd.DataFrame({a: (A[A.tag == a].groupby('k').size() / n_all).reindex(keys).fillna(0) for a in aspects})
pn, pt = F[[f'net_{a}' for a in aspects]], F[[f'talk_{a}' for a in aspects]]
# nearest-neighbour assignment leaves a few more sentences unassigned than HDBSCAN did on the pool,
# which would make every talk rate a little lower; rescale by the ratio of assigned shares
_pool = pd.read_csv(f'{OUT}/sentences.csv', usecols=['topic']).topic
_pool_share = float(_pool.isin(T.topic_id[T.tag != 'noise']).mean()); _ref_share = float((S.topic >= 0).mean())
talk = talk * (_pool_share / _ref_share)
print('talk-rate calibration', round(_pool_share, 3), '/', round(_ref_share, 3))
zr = np.hstack([((net.values - pn.mean().values) / pn.std().replace(0, 1).values), ((talk.values - pt.mean().values) / pt.std().replace(0, 1).values)])
zp = np.hstack([((pn - pn.mean()) / pn.std().replace(0, 1)).values, ((pt - pt.mean()) / pt.std().replace(0, 1)).values])

RAT = pd.read_csv(f'{D}/ratings_all.csv'); RAT['k'] = RAT.k.replace({'ikeabistrodowntown': 'ikeanorthyork'})
RAT = RAT.groupby(['person', 'k'], as_index=False).pct.mean()
pos = {k: i for i, k in enumerate(F.index)}
cand = json.load(open(f'{DATA}/ref_cand.json'))
info = pd.DataFrame(cand.values()).set_index('slug')
Pred = {}
for who, g in RAT.groupby('person'):
    g = g[g.k.isin(pos)]; idx = np.array([pos[k] for k in g.k]); y = g.pct.values
    rg = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(zp[idx], y)
    pool_pred = rg.predict(zp[idx]); ref_pred = rg.predict(zr)
    # express each reference score as where it would land among the person's own predicted places (0-100)
    Pred[who] = pd.Series([(pool_pred < v).mean() for v in ref_pred], index=keys)
Pr = pd.DataFrame(Pred)
# standardized features (pool scale) for plotting the new places alongside the rated ones
pd.DataFrame(zr, index=keys, columns=[f'net_{a}' for a in aspects] + [f'talk_{a}' for a in aspects]).round(4).to_csv(f'{OUT}/ref_features_z.csv')
RULES = {'average': lambda M: M.mean(axis=1), 'least_misery': lambda M: M.min(axis=1),
         'average_without_misery': lambda M: M.mean(axis=1).where(M.min(axis=1) >= 0.35, -1),
         'multiplicative': lambda M: M.prod(axis=1), 'borda': lambda M: M.rank().sum(axis=1)}
recs = {}
for group in [('wael',), ('zed',), ('wael', 'zed')]:
    for rule in (['average'] if len(group) == 1 else RULES):
        g = RULES[rule](Pr[list(group)])
        out = pd.DataFrame({'group_score': g}).join(Pr[list(group)].add_suffix('_pct')).join(info[['title', 'stars', 'nrev', 'hood', 'price']])
        out['spread'] = Pr[list(group)].max(axis=1) - Pr[list(group)].min(axis=1)
        out = out.sort_values('group_score', ascending=False)
        gid = '+'.join(group); out.round(3).to_csv(f'{OUT}/refrecs_{gid}_{rule}.csv'); recs[f'{gid}|{rule}'] = out.head(20)
        print(gid, rule, out.title.head(8).tolist())
Pr.join(info[['title', 'stars', 'nrev', 'hood']]).round(3).to_csv(f'{OUT}/ref_predictions.csv')
# crowd check: Yelp stars of top picks vs. the reference set (stars were never an input)
chk = {}
for k, v in recs.items():
    if k.endswith('average'):
        chk[k] = dict(top20_mean_stars=round(float(v.stars.mean()), 2), ref_mean_stars=round(float(info.loc[keys, 'stars'].mean()), 2),
                      top20_below_3_5=v.title[v.stars < 3.5].tolist(),
                      spearman_pred_vs_stars=round(float(pd.Series(Pr[k.split('|')[0].split('+')].mean(axis=1)).corr(info.loc[keys, 'stars'], method='spearman')), 3))
print(json.dumps(chk, indent=1))
json.dump(dict(n_ref=len(keys), assigned_share=round(float((S.topic >= 0).mean()), 3), crowd_check=chk), open(f'{OUT}/ref_summary.json', 'w'), indent=1)
