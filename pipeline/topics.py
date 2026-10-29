"""v4 stage A: load browser output, sentiment-split topic models (pos / neu / neg), c-TF-IDF names.
Usage: python3 topics.py <prefix>   (reads <prefix>_meta.json, <prefix>_emb.bin, <prefix>_sent.bin from data/)
Writes out/sentences.parquet-like csv, out/topics.csv, out/topic_stability.json"""
import sys, os, json, re
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
import numpy as np, pandas as pd
import umap, hdbscan
from sklearn.metrics import adjusted_rand_score
from sklearn.feature_extraction.text import CountVectorizer

D = os.path.dirname(os.path.abspath(__file__)); PRE = sys.argv[1] if len(sys.argv) > 1 else 'v4'
OUT = f'{D}/out'; os.makedirs(OUT, exist_ok=True)
meta = json.load(open(f'{DATA}/{PRE}_meta.json'))
n = len(meta['sent'])
def load_chunks(stage, dim):
    # chunks were written in length-sorted order (meta['order']); put rows back in sentence order
    order = np.array(meta['order']); C = meta['chunk']; out = np.zeros((n, dim), np.float32)
    for c in range(int(np.ceil(n / C))):
        ids = order[c * C:(c + 1) * C]
        out[ids] = np.fromfile(f'{DATA}/{PRE}_{stage}_chunk_{c}.bin', dtype=np.float32).reshape(len(ids), dim)
    return out
E = load_chunks('emb', 768); P3 = load_chunks('sent', 3)
assert np.allclose(np.linalg.norm(E, axis=1), 1, atol=1e-3), 'embeddings not unit length'
assert np.allclose(P3.sum(1), 1, atol=1e-3), 'sentiment rows do not sum to 1'
places = pd.DataFrame(meta['places']); reviews = pd.DataFrame(meta['reviews'])
S = pd.DataFrame(meta['sent'], columns=['p', 'r', 'text'])
S['k'] = places.k.values[S.p.values]
S['stars'] = reviews.stars.values[S.r.values]; S['src'] = reviews.src.values[S.r.values]
S[['neg', 'neu', 'pos']] = P3
S['pol'] = np.array(['neg', 'neu', 'pos'])[P3.argmax(1)]
S['sent_score'] = P3[:, 2] - P3[:, 0]   # -1..1
# restaurants with too few reviews are dropped from features (doc step 5: min 10 reviews)
# all sentences feed the topic model; the minimum-review rule is applied per restaurant in model.py
nrev = reviews.groupby('p').size().reindex(range(len(places)), fill_value=0)
places['nrev'] = nrev.values; places.to_csv(f'{OUT}/places.csv', index=False)
print('places', len(places), '| sentences', len(S), '| polarity share', S.pol.value_counts(normalize=True).round(3).to_dict())

STOP = list(CountVectorizer(stop_words='english').get_stop_words()) + ['place', 'food', 'really', 'just', 'like', 'definitely', 'got', 've', 'll', 'don']
def ctfidf(texts, labels, top=10):
    cv = CountVectorizer(stop_words=STOP, ngram_range=(1, 2), min_df=3, token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]+\b')
    X = cv.fit_transform(texts); voc = np.array(cv.get_feature_names_out())
    labs = sorted(set(labels) - {-1})
    M = np.vstack([np.asarray(X[labels == l].sum(0)).ravel() for l in labs]).astype(float)
    tf = M / np.maximum(M.sum(1, keepdims=True), 1); idf = np.log(1 + M.sum(1).mean() / (M.sum(0) + 1))
    sc = tf * idf
    return {l: list(voc[np.argsort(-sc[i])][:top]) for i, l in enumerate(labs)}

os.makedirs(f'{OUT}/cache', exist_ok=True)
def umap5(idx, seed):
    f = f'{OUT}/cache/umap_{len(idx)}_{seed}.npy'
    if os.path.exists(f): return np.load(f)
    U = umap.UMAP(n_neighbors=15, n_components=5, metric='cosine', min_dist=0.0, random_state=seed).fit_transform(E[idx])
    np.save(f, U); return U
def fit(idx, mcs, seed):
    return hdbscan.HDBSCAN(min_cluster_size=mcs, min_samples=10, cluster_selection_method='eom').fit_predict(umap5(idx, seed))

topics, assign, stab = [], np.full(len(S), -1), {}
for pol in ['pos', 'neu', 'neg']:
    idx = np.where(S.pol == pol)[0]
    grid = sorted({max(15, int(len(idx) * f)) for f in (0.002, 0.004, 0.008)})
    best = None
    for mcs in grid:
        labs = [fit(idx, mcs, s) for s in range(3)]
        aris = [adjusted_rand_score(labs[0][labs[0] >= 0], labs[j][labs[0] >= 0]) for j in (1, 2)]
        nt = len(set(labs[0]) - {-1}); noise = float((labs[0] == -1).mean())
        stab[f'{pol}_{mcs}'] = dict(n=len(idx), topics=nt, noise=round(noise, 3), seed_ari=round(float(np.mean(aris)), 3))
        print(pol, stab[f'{pol}_{mcs}'])
        sc = np.mean(aris) - (0.5 if nt < 6 else 0) - (0.3 if noise > 0.55 else 0) - (0.2 if nt > 80 else 0)
        if best is None or sc > best[0]: best = (sc, mcs, labs[0])
    _, mcs, lab = best
    print(pol, 'chosen min_cluster_size', mcs)
    tw = ctfidf(S.text.values[idx], lab)
    for l, words in tw.items():
        sel = idx[lab == l]; cen = E[sel].mean(0); cen /= np.linalg.norm(cen)
        rep = S.text.values[sel[np.argsort(-(E[sel] @ cen))[:6]]].tolist()
        tid = len(topics)
        topics.append(dict(topic_id=tid, polarity=pol, size=int(len(sel)), n_rest=int(len(set(S.k.values[sel]))),
                           top_words=', '.join(words), examples=' || '.join(rep)))
        assign[sel] = tid
T = pd.DataFrame(topics); S['topic'] = assign
# merge near-duplicate topics within polarity (centroid cosine > 0.85)
cent = np.vstack([E[S.topic.values == t].mean(0) for t in T.topic_id]); cent /= np.linalg.norm(cent, axis=1, keepdims=True)
merged = {}
for i in range(len(T)):
    for j in range(i + 1, len(T)):
        if T.polarity[i] == T.polarity[j] and cent[i] @ cent[j] > 0.85 and j not in merged:
            merged[j] = merged.get(i, i)
for j, i in merged.items(): S.loc[S.topic == j, 'topic'] = i
T = T[~T.topic_id.isin(merged)].reset_index(drop=True)
T['size'] = T.topic_id.map(S.topic.value_counts()).astype(int)
print('topics', T.groupby('polarity').size().to_dict(), 'merged', len(merged), '| noise share', round((S.topic == -1).mean(), 3))
T.to_csv(f'{OUT}/topics_raw.csv', index=False)
S.to_csv(f'{OUT}/sentences.csv', index=False)
np.save(f'{OUT}/emb_kept.npy', E)
json.dump(stab, open(f'{OUT}/topic_stability.json', 'w'), indent=1)
