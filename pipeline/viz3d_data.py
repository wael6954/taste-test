"""Data for the 3D page: (A) restaurants on three interpretable axes, (B) each person's prediction surface,
(C) a 3D map of review sentences coloured by aspect."""
import json, numpy as np, pandas as pd, umap
from sklearn.linear_model import RidgeCV
F = pd.read_csv('out/features_v4.csv', index_col='k')
RST = pd.read_csv('restaurants.csv').set_index('k')
aspects = [c[4:] for c in F if c.startswith('net_')]
net = F[[f'net_{a}' for a in aspects]]; talk = F[[f'talk_{a}' for a in aspects]]
z = lambda d: (d - d.mean()) / d.std().replace(0, 1)
netz, talkz = z(net), z(talk)
X = np.hstack([netz.values, talkz.values]); cols = [f'net_{a}' for a in aspects] + [f'talk_{a}' for a in aspects]
RAT = pd.read_csv('ratings_all.csv'); RAT['k'] = RAT.k.replace({'ikeabistrodowntown': 'ikeanorthyork'})
RAT = RAT.groupby(['person', 'k'], as_index=False).pct.mean()
pos = {k: i for i, k in enumerate(F.index)}
out = {'places': [], 'surf': {}, 'coef': {}}
models = {}
for who, g in RAT.groupby('person'):
    g = g[g.k.isin(pos)]; idx = np.array([pos[k] for k in g.k])
    m = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(X[idx], g.pct.values); models[who] = m
    out['coef'][who] = dict(zip(cols, np.round(m.coef_, 4)))
pred = {w: m.predict(X) for w, m in models.items()}
# rank-scale predictions so 0..1 means 'where it lands among all pool places'
rk = {w: (pd.Series(p).rank().values - 0.5) / len(p) for w, p in pred.items()}
mem = pd.read_csv('out/memberships_v4.csv', index_col=0)
CL = {'c0': 'Popular, worth the wait', 'c1': 'Cheap and basic', 'c2': 'Sit-down: ambience & service', 'c3': 'Flavour-first, slow prep', 'c4': 'Casual brunch, lunch & dates', 'c5': 'Complaint-heavy'}
mcols = [c for c in mem.columns if c.startswith('c')]
for i, k in enumerate(F.index):
    r = {'k': k, 'name': RST.name.get(k, k), 'fam': RST.family.get(k, ''), 'x': round(float(netz.loc[k, 'net_flavor']), 3), 'y': round(float(netz.loc[k, 'net_service']), 3),
         'z': round(float(talkz.loc[k, 'talk_wait']), 3), 'cl': CL[mem.loc[k, mcols].astype(float).idxmax()] if k in mem.index else ''}
    for w in models:
        a = RAT[(RAT.person == w) & (RAT.k == k)].pct
        r[w] = round(float(a.iloc[0]), 3) if len(a) else None
        r[w + '_pred'] = round(float(rk[w][i]), 3)
    out['places'].append(r)
# reference set (new places), placed with the same pool-scaled features
import os
out['ref'] = []
if os.path.exists('out/ref_features_z.csv'):
    RZ = pd.read_csv('out/ref_features_z.csv', index_col=0); RP = pd.read_csv('out/ref_predictions.csv', index_col=0)
    for k in RZ.index:
        out['ref'].append({'k': k, 'name': RP.title.get(k, k), 'x': round(float(RZ.loc[k, 'net_flavor']), 3), 'y': round(float(RZ.loc[k, 'net_service']), 3),
                           'z': round(float(RZ.loc[k, 'talk_wait']), 3), 'wael': round(float(RP.wael[k]), 3), 'zed': round(float(RP.zed[k]), 3), 'stars': float(RP.stars[k])})
# surfaces: vary flavour and service praise, everything else at its average (0); height = predicted percentile
grid = np.linspace(-2.5, 2.5, 26)
for w, m in models.items():
    fi, si = cols.index('net_flavor'), cols.index('talk_wait')
    Zs = []
    for sv in grid:
        row = []
        for fv in grid:
            v = np.zeros(len(cols)); v[fi] = fv; v[si] = sv; row.append(float(m.predict(v[None])[0]))
        Zs.append(row)
    out['surf'][w] = dict(grid=np.round(grid, 2).tolist(), z=np.round(Zs, 3).tolist())
# review galaxy: 3D UMAP of a sample of assigned sentences
S = pd.read_csv('out/sentences.csv', usecols=['k', 'text', 'topic', 'pol']); E = np.load('out/emb_kept.npy')
T = pd.read_csv('out/topics_tagged.csv').set_index('topic_id')
ok = S.topic.isin(T.index[T.tag != 'noise']).values
idx = np.where(ok)[0]; rng = np.random.default_rng(0); idx = rng.choice(idx, 9000, replace=False)
U = umap.UMAP(n_components=3, n_neighbors=30, min_dist=0.15, metric='cosine', random_state=0).fit_transform(E[idx])
U = (U - U.mean(0)) / U.std(0)
tag = T.tag.reindex(S.topic.values[idx]).values; name = T.name.reindex(S.topic.values[idx]).values
gal = {'x': np.round(U[:, 0], 2).tolist(), 'y': np.round(U[:, 1], 2).tolist(), 'z': np.round(U[:, 2], 2).tolist(),
       'tag': tag.tolist(), 'pol': S.pol.values[idx].tolist(), 'topic': name.tolist(),
       'text': [t[:110] for t in S.text.values[idx]]}
lab = []
for t in pd.Series(S.topic.values[idx]).value_counts().index[:28]:
    m = S.topic.values[idx] == t
    lab.append(dict(name=T.name[t], tag=T.tag[t], pol=T.polarity[t], x=round(float(U[m, 0].mean()), 2), y=round(float(U[m, 1].mean()), 2), z=round(float(U[m, 2].mean()), 2)))
gal['labels'] = lab
out['galaxy'] = gal
json.dump(out, open('out/viz3d_data.json', 'w'))
print(len(out['places']), {w: sorted(out['coef'][w].items(), key=lambda x: -abs(x[1]))[:4] for w in out['coef']})
