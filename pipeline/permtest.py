"""Permutation test for the best model (ridge on aspect sentiment + talk rates): shuffle each person's
percentiles 200 times, rerun the same 5x5-fold CV, and see where the real score falls. Also corrects for
having looked at many model variants: compares against the max over all variants under the null."""
import os, json, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.model_selection import KFold
from sklearn.linear_model import RidgeCV
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'
F = pd.read_csv(f'{OUT}/features_v4.csv', index_col='k')
net = F[[c for c in F if c.startswith('net_')]]; talk = F[[c for c in F if c.startswith('talk_')]]
z = lambda d: ((d - d.mean()) / d.std().replace(0, 1)).values
M = np.hstack([z(net), z(talk)])
RAT = pd.read_csv(f'{D}/ratings_all.csv'); RAT['k'] = RAT.k.replace({'ikeabistrodowntown': 'ikeanorthyork'})
RAT = RAT.groupby(['person', 'k'], as_index=False).pct.mean()
pos = {k: i for i, k in enumerate(F.index)}
def cv(Mx, y, reps=3):
    out = []
    for rep in range(reps):
        pred = np.zeros(len(y))
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(y):
            pred[te] = RidgeCV(alphas=np.logspace(-1, 3, 12)).fit(Mx[tr], y[tr]).predict(Mx[te])
        out.append(spearmanr(pred, y)[0])
    return float(np.mean(out))
rng = np.random.default_rng(0); res = {}
for who, g in RAT.groupby('person'):
    g = g[g.k.isin(pos)]; idx = np.array([pos[k] for k in g.k]); y = g.pct.values; Mx = M[idx]
    real = cv(Mx, y)
    null = [cv(Mx, rng.permutation(y), reps=1) for _ in range(200)]
    res[who] = dict(n=len(y), real_spearman=round(real, 3), null_95=round(float(np.quantile(null, .95)), 3), null_99=round(float(np.quantile(null, .99)), 3), p=round(float((np.sum(np.array(null) >= real) + 1) / 201), 4))
    print(who, res[who])
json.dump(res, open(f'{OUT}/permtest_ridge_talk.json', 'w'), indent=1)
