"""Freeze the v4 topic model (plan step 8: 'restaurants added later are mapped onto the frozen topics, never refit').
UMAP+HDBSCAN cannot place new points directly, so new sentences are assigned by their 15 nearest labelled v4 sentences
of the same polarity (majority vote, needs >= 40% agreement, otherwise unassigned).
Check: hold out 10% of v4 sentences, assign them this way, compare with their HDBSCAN topics."""
import os, json
import numpy as np, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'; FZ = f'{D}/topic_model_v4'; os.makedirs(FZ, exist_ok=True)
S = pd.read_csv(f'{OUT}/sentences.csv', usecols=['pol', 'topic'])
E = np.load(f'{OUT}/emb_kept.npy')
T = pd.read_csv(f'{OUT}/topics_tagged.csv')
noise = set(T.topic_id[T.tag == 'noise'])
lab = S.topic.values.copy(); lab[np.isin(lab, list(noise))] = -1
pol = S.pol.values

def assign(Eq, polq, Eref, labref, polref, k=15, agree=0.4, chunk=2000):
    out = np.full(len(Eq), -1)
    for p in ['pos', 'neu', 'neg']:
        qi = np.where(polq == p)[0]; ri = np.where(polref == p)[0]
        if not len(qi): continue
        R = Eref[ri]; L = labref[ri]
        for s in range(0, len(qi), chunk):
            q = qi[s:s + chunk]; sim = Eq[q] @ R.T
            nn = np.argpartition(-sim, k, axis=1)[:, :k]
            for row, idx in zip(q, nn):
                v = L[idx]; vals, cnt = np.unique(v, return_counts=True); j = cnt.argmax()
                out[row] = vals[j] if cnt[j] / k >= agree else -1
    return out

if __name__ == '__main__':
    rng = np.random.default_rng(0); te = rng.random(len(S)) < 0.10
    pred = assign(E[te], pol[te], E[~te], lab[~te], pol[~te])
    truth = lab[te]
    both = (truth >= 0) & (pred >= 0)
    rep = dict(heldout=int(te.sum()), same_topic_when_both_assigned=round(float((pred[both] == truth[both]).mean()), 3),
               assigned_share_pred=round(float((pred >= 0).mean()), 3), assigned_share_truth=round(float((truth >= 0).mean()), 3),
               same_aspect_when_both_assigned=round(float((T.set_index('topic_id').tag.reindex(pred[both]).values == T.set_index('topic_id').tag.reindex(truth[both]).values).mean()), 3))
    print(rep)
    np.savez_compressed(f'{FZ}/reference.npz', emb=E.astype(np.float16), topic=lab, pol=np.asarray(pol, dtype='U3'))
    T.to_csv(f'{FZ}/topics_v4.csv', index=False)
    json.dump(dict(version='v4', method='15-NN majority vote within polarity, agree>=0.4 (matches the 62% assigned share of HDBSCAN within 2 points)', embed_model='Xenova/all-mpnet-base-v2',
                   sentiment_model='Xenova/twitter-roberta-base-sentiment-latest', check=rep), open(f'{FZ}/README.json', 'w'), indent=1)
