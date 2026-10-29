"""Compare LLM opinion units (hand-extracted for 100 random reviews) with the sentence pipeline on the same reviews."""
import json, os, numpy as np, pandas as pd
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
idx = json.load(open(f'{DATA}/opinion_units/sample_idx.json'))
U = pd.DataFrame(json.load(open(f'{DATA}/opinion_units/units_1.json')) + json.load(open(f'{DATA}/opinion_units/units_2.json')), columns=['j', 'aspect', 'excerpt', 'sent'])
U['r'] = [idx[j] for j in U.j]
S = pd.read_csv('out/sentences.csv'); T = pd.read_csv('out/topics_tagged.csv').set_index('topic_id')
S = S[S.r.isin(idx)].copy(); S['tag'] = S.topic.map(T.tag).fillna('unassigned')
def pol(x, lo, hi): return 'pos' if x > hi else 'neg' if x < lo else 'neu'
L = U.groupby(['r', 'aspect']).sent.mean().apply(lambda v: pol(v, 4.5, 5.5)).rename('llm')
Pp = S[~S.tag.isin(['what', 'noise', 'unassigned'])].groupby(['r', 'tag']).sent_score.mean().apply(lambda v: pol(v, -0.2, 0.2)).rename('pipe')
Pp.index.names = ['r', 'aspect']
J = pd.concat([L, Pp], axis=1)
both = J.dropna()
res = dict(
    reviews=len(idx), llm_units=len(U), units_per_review=round(len(U) / len(idx), 2),
    sentences=len(S), sentences_per_review=round(len(S) / len(idx), 2),
    pipeline_sentences_unassigned_or_dish=round(float(S.tag.isin(['what', 'noise', 'unassigned']).mean()), 3),
    review_aspects_llm=int(L.notna().sum()), review_aspects_pipeline=int(Pp.notna().sum()),
    recall_of_llm_aspects=round(len(both) / len(L), 3), precision_vs_llm=round(len(both) / len(Pp), 3),
    polarity_agreement_on_shared=round(float((both['llm'] == both['pipe']).mean()), 3),
    negative_llm_aspects=int((L == 'neg').sum()),
    negative_recall=round(float(((J.llm == 'neg') & (J['pipe'] == 'neg')).sum() / max((J.llm == 'neg').sum(), 1)), 3),
)
per = {}
for a, g in J.groupby(level='aspect'):
    per[a] = dict(llm=int(g['llm'].notna().sum()), found=int((g['llm'].notna() & g['pipe'].notna()).sum()), pipe_only=int((g['llm'].isna() & g['pipe'].notna()).sum()))
res['by_aspect'] = per
# how often one sentence holds 2+ opinions: units whose review has more units than sentences
res['reviews_with_more_units_than_sentences'] = int((U.groupby('r').size() > S.groupby('r').size().reindex(U.r.unique()).fillna(0)).sum())
json.dump(res, open('out/opinion_unit_test.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
