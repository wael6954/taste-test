"""v4 stage B: restaurant features -> overlapping clusters -> taste profiles -> held-out validation.
Needs out/sentences.csv, out/topics_tagged.csv (topic_id, polarity, tag, name), restaurants.csv, ratings_all.csv."""
import os, json, re, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from sklearn.metrics import roc_auc_score, adjusted_rand_score
from sklearn.model_selection import KFold
from sklearn.linear_model import RidgeCV
import skfuzzy as fuzz

D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'
rng = np.random.default_rng(0)
S = pd.read_csv(f'{OUT}/sentences.csv')
E = np.load(f'{OUT}/emb_kept.npy')
T = pd.read_csv(f'{OUT}/topics_tagged.csv')
RST = pd.read_csv(f'{D}/restaurants.csv').set_index('k')
RAT = pd.read_csv(f'{D}/ratings_all.csv')
# both IKEA entries matched the same Yelp listing: treat as one restaurant
RAT['k'] = RAT.k.replace({'ikeabistrodowntown': 'ikeanorthyork'}); RAT = RAT.groupby(['person', 'k'], as_index=False).pct.mean()
noise_ids = set(T.topic_id[T.tag == 'noise'])
S.loc[S.topic.isin(noise_ids), 'topic'] = -1          # meta talk about ratings/reviews carries no taste information
T = T[T.tag != 'noise'].reset_index(drop=True)
TAG = dict(zip(T.topic_id, T.tag))

MINREV = 5   # plan said 10; 26 rated places have 5-9 reviews, so 5 keeps them with shrinkage on sparse aspects
PL = pd.read_csv(f'{OUT}/places.csv')
keys = sorted(set(PL.k[PL.nrev >= MINREV]) & set(S.k))
_m = S.k.isin(keys).values; S = S[_m].reset_index(drop=True); E = E[_m]
print('restaurants with >=', MINREV, 'reviews:', len(keys))
n_all = S.groupby('k').size().reindex(keys)
A = S[S.topic >= 0].copy(); A['tag'] = A.topic.map(TAG)
cnt = pd.crosstab(A.k, A.topic).reindex(index=keys, columns=T.topic_id, fill_value=0)
share = cnt.div(n_all, axis=0)

# ---------- features ----------
# 1) sentiment-split topic shares (doc step 9), each topic standardized
share_z = (share - share.mean()) / share.std().replace(0, 1)
how_ids = T.topic_id[T.tag != 'what'].values
what_ids = T.topic_id[T.tag == 'what'].values
# 2) net sentiment per aspect: uses the 3-class sentiment of every sentence that a topic assigns to that aspect
aspects = sorted(set(T.tag) - {'what'})
net, talk = {}, {}
for a in aspects:
    sub = A[A.tag == a]
    g = sub.groupby('k').sent_score
    net[a] = (g.sum() / (g.size() + 2)).reindex(keys).fillna(0)   # shrunk to 0 with few mentions
    talk[a] = (g.size() / n_all).reindex(keys).fillna(0)
net = pd.DataFrame(net); talk = pd.DataFrame(talk)
netz = (net - net.mean()) / net.std().replace(0, 1)
# 3) cuisine family + price
fam = RST.family.reindex(keys).fillna('other')
cu = pd.get_dummies(fam).astype(float)
pr = RST.price.reindex(keys); pr = ((pr - pr.mean()) / pr.std()).fillna(0).to_frame('price')
# 4) mean embedding baseline
mean_emb = pd.DataFrame(np.vstack([E[S.k.values == k].mean(0) for k in keys]), index=keys)
# 5) cuisine-relative aspects (each aspect vs. the typical place of the same cuisine, shrunk for small cuisines)
def rel(df, m=5.0):
    g = df.groupby(fam.values); mu = g.transform('mean'); n = g.transform('count')
    return df - (n * mu + m * df.mean()) / (n + m)
net_rel = rel(netz)

def blocks(*Ms):
    out = []
    for M in Ms:
        M = np.asarray(M, float); M = M - M.mean(0); nn = np.linalg.norm(M)
        out.append(M / (nn if nn > 0 else 1) * np.sqrt(M.shape[0]))
    return np.hstack(out)
FEATS = {
    'topics_sentiment_split': blocks(share_z.values, cu.values, pr.values),
    'how_topics+aspects': blocks(share_z[how_ids].values, netz.values, cu.values, pr.values),
    'aspects_cuisine_relative': blocks(net_rel.values, share_z[what_ids].values, pr.values),
    'mean_embedding': blocks(mean_emb.values, cu.values, pr.values),
}
feat_tbl = pd.concat([net.add_prefix('net_'), talk.add_prefix('talk_'), share.add_prefix('t'), cu, pr], axis=1); feat_tbl.index.name = 'k'
feat_tbl.round(4).to_csv(f'{OUT}/features_v4.csv')

# ---------- ratings ----------
R = {}
for who, g in RAT.groupby('person'):
    pc = g.set_index('k').pct
    R[who] = pc[pc.index.isin(keys)]
print({w: len(v) for w, v in R.items()}, 'restaurants', len(keys))

# ---------- clustering ----------
def pca(X): return PCA(n_components=8, random_state=0).fit_transform(X)   # 8 dims as in v3; fuzzy c-means collapses to duplicate centres in high dimensions
def gmm(Z, k, seed=0): return GaussianMixture(k, covariance_type='diag', n_init=5, random_state=seed, reg_covar=1e-3).fit(Z)
def fcm(Z, k, m=1.5, seed=0):
    _, u, *_ = fuzz.cluster.cmeans(Z.T, k, m, error=1e-5, maxiter=1000, seed=seed); return u.T
ksel = {}
for name in ['topics_sentiment_split', 'how_topics+aspects', 'aspects_cuisine_relative']:
    Z = pca(FEATS[name]); ksel[name] = {}
    for k in range(4, 13):
        g = gmm(Z, k); lab = g.predict(Z); aris = []
        for b in range(10):
            ii = rng.choice(len(Z), len(Z), replace=True)
            aris.append(adjusted_rand_score(lab, gmm(Z[ii], k, b).predict(Z)))
        ksel[name][k] = dict(bic=round(float(g.bic(Z)), 1), boot_ari=round(float(np.mean(aris)), 3))
    print(name, {k: v['boot_ari'] for k, v in ksel[name].items()})
json.dump(ksel, open(f'{OUT}/k_selection.json', 'w'), indent=1)
def pick_k(d):
    ok = [k for k in d if 5 <= k <= 10 and d[k]['boot_ari'] >= 0.5]
    return max(ok, key=lambda k: d[k]['boot_ari']) if ok else max([k for k in d if 5 <= k <= 10], key=lambda k: d[k]['boot_ari'])
K = {n: pick_k(d) for n, d in ksel.items()}; K['mean_embedding'] = K['topics_sentiment_split']
print('chosen K', K)

# ---------- scorers ----------
def prof_score(mem, tr, y_tr, te, m=3.0):
    W = mem[tr]; prof = (W.T @ y_tr + m * y_tr.mean()) / (W.sum(0) + m); return mem[te] @ prof
def knn_score(Xn, tr, y_tr, te, k=10, m=2.0):
    sims = Xn[te] @ Xn[tr].T; out = []
    for row in sims:
        nn = np.argsort(-row)[:k]; w = np.clip(row[nn], 0, None)
        out.append((w @ y_tr[nn] + m * y_tr.mean()) / (w.sum() + m))
    return np.array(out)
pos = {k: i for i, k in enumerate(keys)}
def cv(pred_fn, y, reps=5):
    sp, auc = [], []
    for rep in range(reps):
        pred = np.zeros(len(y))
        for tr, te in KFold(5, shuffle=True, random_state=rep).split(y): pred[te] = pred_fn(tr, te)
        sp.append(spearmanr(pred, y)[0]); auc.append(roc_auc_score(y >= np.quantile(y, 2 / 3), pred))
    return dict(spearman=round(float(np.mean(sp)), 3), auc_top3=round(float(np.mean(auc)), 3))

val = {}; MEM = {}
for name, X in FEATS.items():
    Z = pca(X); Xn = Z / np.linalg.norm(Z, axis=1, keepdims=True)
    memF = fcm(Z, K[name]); memG = gmm(Z, K[name]).predict_proba(Z); MEM[name] = (memF, memG, Z)
    for who, pc in R.items():
        idx = np.array([pos[k] for k in pc.index]); y = pc.values
        for scorer, fn in [('cluster_fcm', lambda tr, te: prof_score(memF[idx], tr, y[tr], te)),
                           ('cluster_gmm', lambda tr, te: prof_score(memG[idx], tr, y[tr], te)),
                           ('knn', lambda tr, te: knn_score(Xn[idx], tr, y[tr], te))]:
            val[f'{name}|{scorer}|{who}'] = dict(n=len(y), K=K[name], **cv(fn, y))
# personal aspect regression (the model that worked for Wael in v3)
for feat, M in [('ridge_aspects', netz.values), ('ridge_aspects_cuisine_relative', net_rel.values),
                ('ridge_aspects+talk', np.hstack([netz.values, ((talk - talk.mean()) / talk.std().replace(0, 1)).values]))]:
    for who, pc in R.items():
        idx = np.array([pos[k] for k in pc.index]); y = pc.values
        val[f'{feat}|{who}'] = dict(n=len(y), **cv(lambda tr, te: RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(M[idx][tr], y[tr]).predict(M[idx][te]), y))
# baselines: cuisine mean, person's average (constant -> AUC 0.5), random null
for who, pc in R.items():
    idx = np.array([pos[k] for k in pc.index]); y = pc.values; fv = fam.values[idx]
    def cui(tr, te):
        mu = pd.Series(y[tr]).groupby(fv[tr]).agg(['sum', 'count'])
        return np.array([((mu.loc[f, 'sum'] if f in mu.index else 0) + 3 * y[tr].mean()) / ((mu.loc[f, 'count'] if f in mu.index else 0) + 3) for f in fv[te]])
    val[f'baseline_cuisine_mean|{who}'] = dict(n=len(y), **cv(cui, y))
    top = y >= np.quantile(y, 2 / 3)
    null = [roc_auc_score(top, rng.random(len(y))) for _ in range(2000)]
    val[f'null|{who}'] = dict(n=len(y), auc_95=round(float(np.quantile(null, .95)), 3), spearman_95=round(1.96 / np.sqrt(len(y) - 1), 3))
json.dump(val, open(f'{OUT}/validation_v4.json', 'w'), indent=1)
for k, v in val.items(): print(k, v)

# single-aspect correlations (retest of the v3 portions / service finding)
asp = {}
for who, pc in R.items():
    for a in aspects:
        r1 = spearmanr(net.loc[pc.index, a], pc.values); r2 = spearmanr(net_rel.loc[pc.index, a], pc.values)
        asp[f'{who}|{a}'] = dict(plain=[round(float(r1[0]), 3), round(float(r1[1]), 3)], within_cuisine=[round(float(r2[0]), 3), round(float(r2[1]), 3)])
json.dump(asp, open(f'{OUT}/aspect_correlations_v4.json', 'w'), indent=1)
print('aspect rho (plain | within cuisine), p<0.1 shown:')
for k, v in asp.items():
    if min(v['plain'][1], v['within_cuisine'][1]) < 0.1: print(' ', k, v)

# ---------- final structure: main clusters ----------
MAIN = 'how_topics+aspects'
memF, memG, Z = MEM[MAIN]
Mem = pd.DataFrame(memF, index=keys, columns=[f'c{i}' for i in range(K[MAIN])])
Mem['family'] = fam.values
Mem.to_csv(f'{OUT}/memberships_v4.csv')
np.save(f'{OUT}/Z_main.npy', Z)
Mm = Mem.drop(columns='family')
desc, taste = [], {w: [] for w in R}
for c in Mm.columns:
    wt = Mm[c]
    nz = (netz.mul(wt, axis=0).sum() / wt.sum()).sort_values()
    hz = (share_z[how_ids].mul(wt, axis=0).sum() / wt.sum()).sort_values(ascending=False)
    cc = cu.mul(wt, axis=0).sum().sort_values(ascending=False)
    row = dict(cluster=c, size=int((wt >= 0.2).sum()),
               best_aspects=', '.join(f'{a} {v:+.2f}' for a, v in nz[::-1][:3].items()),
               worst_aspects=', '.join(f'{a} {v:+.2f}' for a, v in nz[:2].items()),
               top_topics=' | '.join(T.set_index('topic_id').loc[t, 'name'] for t in hz.index[:3]),
               cuisines=', '.join(cc.index[:3]),
               members=', '.join(RST.name.reindex(wt[wt >= 0.2].sort_values(ascending=False).index[:10]).fillna('').values))
    for who, pc in R.items():
        w_ = wt[pc.index]; prof = float((w_ @ pc + 3 * pc.mean()) / (w_.sum() + 3))
        row[who] = round(prof, 3); row[who + '_n'] = round(float(w_.sum()), 1)
        taste[who].append(dict(cluster=c, weighted_pct=round(prof, 3), effective_n=round(float(w_.sum()), 1)))
    desc.append(row)
pd.DataFrame(desc).to_csv(f'{OUT}/clusters_v4.csv', index=False)
for who in R: pd.DataFrame(taste[who]).sort_values('weighted_pct', ascending=False).to_csv(f'{OUT}/taste_{who}.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 80)
print(pd.DataFrame(desc).drop(columns='members').to_string())
print('overlap (2+ memberships >= 0.2):', round(((Mm >= 0.2).sum(1) >= 2).mean(), 2))
json.dump(dict(K=K, main=MAIN, aspects=aspects, n_rest=len(keys), n_sent=int(len(S))), open(f'{OUT}/model_summary.json', 'w'))

# ---------- full-data predictions for every restaurant, per person and method ----------
pred = {}
memF_main = MEM[MAIN][0]; Zm = MEM[MAIN][2]; Xn_main = Zm / np.linalg.norm(Zm, axis=1, keepdims=True)
allidx = np.arange(len(keys))
for who, pc in R.items():
    idx = np.array([pos[k] for k in pc.index]); y = pc.values
    P = pd.DataFrame(index=keys)
    P['cluster'] = prof_score(memF_main, idx, y, allidx)
    P['knn'] = knn_score(Xn_main, idx, y, allidx)
    P['ridge_aspects'] = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(netz.values[idx], y).predict(netz.values)
    P['ridge_cuisine_rel'] = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(net_rel.values[idx], y).predict(net_rel.values)
    MT = np.hstack([netz.values, ((talk - talk.mean()) / talk.std().replace(0, 1)).values])
    rg = RidgeCV(alphas=np.logspace(-1, 3, 20)).fit(MT[idx], y); P['ridge_aspects_talk'] = rg.predict(MT)
    pd.Series(rg.coef_, index=[f'net_{a}' for a in aspects] + [f'talk_{a}' for a in aspects]).round(4).to_csv(f'{OUT}/ridge_coef_{who}.csv')
    P['rated_pct'] = pc.reindex(keys)
    P.index.name = 'k'; P.round(4).to_csv(f'{OUT}/pred_{who}.csv'); pred[who] = P
print('predictions written for', list(pred))
