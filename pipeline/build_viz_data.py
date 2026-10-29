import json, pandas as pd, numpy as np
O = 'out'
val = json.load(open(f'{O}/validation_v4.json')); asp = json.load(open(f'{O}/aspect_correlations_v4.json'))
perm = json.load(open(f'{O}/permtest_ridge_talk.json')); recs = json.load(open(f'{O}/recs_summary.json'))
T = pd.read_csv(f'{O}/topics_tagged.csv'); C = pd.read_csv(f'{O}/clusters_v4.csv'); S = pd.read_csv(f'{O}/sentences.csv', usecols=['pol', 'topic'])
RST = pd.read_csv('restaurants.csv').set_index('k')
methods = [('Clusters (GMM)', 'how_topics+aspects|cluster_gmm'), ('Clusters (fuzzy)', 'how_topics+aspects|cluster_fcm'),
           ('Nearest neighbours', 'how_topics+aspects|knn'), ('Mean embedding, neighbours', 'mean_embedding|knn'),
           ('Cuisine average (baseline)', 'baseline_cuisine_mean'), ('Aspect sentiment (ridge)', 'ridge_aspects'),
           ('Aspects + talk rate (ridge)', 'ridge_aspects+talk')]
V = {who: {'null_sp': val[f'null|{who}']['spearman_95'], 'null_auc': val[f'null|{who}']['auc_95'], 'n': val[f'null|{who}']['n'],
           'perm': perm[who], 'rows': [dict(m=m, sp=val[f'{k}|{who}']['spearman'], auc=val[f'{k}|{who}']['auc_top3']) for m, k in methods]} for who in ['wael', 'zed']}
A = {who: [dict(a=k.split('|')[1], r=v['plain'][0], p=v['plain'][1], rw=v['within_cuisine'][0], pw=v['within_cuisine'][1]) for k, v in asp.items() if k.startswith(who)] for who in ['wael', 'zed']}
coef = {who: pd.read_csv(f'{O}/ridge_coef_{who}.csv', index_col=0).iloc[:, 0].round(4).to_dict() for who in ['wael', 'zed']}
tp = T.assign(n=T.topic_id.map(S.topic.value_counts()).fillna(0).astype(int))
topics = tp[tp.tag != 'noise'].sort_values('n', ascending=False)[['name', 'tag', 'polarity', 'n', 'n_rest']].to_dict('records')
clusters = C.to_dict('records')
R = {}
import glob, os
for f in glob.glob(f'{O}/recs_*.csv'):
    gid_rule = os.path.basename(f)[5:-4]
    d = pd.read_csv(f)
    R[gid_rule] = d.head(12).replace({np.nan: None}).to_dict('records')
stats = dict(restaurants=195, rated_with_features=177, reviews=5818, sentences=int(len(S)), topics=int((T.tag != 'noise').sum()),
             noise_share=round(float((S.topic == -1).mean()), 3), pol=S.pol.value_counts(normalize=True).round(3).to_dict(),
             wael_n=V['wael']['n'], zed_n=V['zed']['n'], both=int(sum(1 for r in R.get('wael+zed_average', []) if r.get('wael_rated') and r.get('zed_rated'))))
REF = {}
for f in glob.glob(f'{O}/refrecs_*.csv'):
    d = pd.read_csv(f).rename(columns={'Unnamed: 0': 'slug'})
    REF[os.path.basename(f)[8:-4]] = d.head(15).replace({np.nan: None}).to_dict('records')
refsum = json.load(open(f'{O}/ref_summary.json')) if os.path.exists(f'{O}/ref_summary.json') else None
json.dump(dict(V=V, A=A, coef=coef, topics=topics, clusters=clusters, R=R, REF=REF, refsum=refsum, stats=stats, choice=recs['choice']), open('out/viz_data.json', 'w'), default=float)
print(json.dumps(stats)); print(list(R)[:20])
