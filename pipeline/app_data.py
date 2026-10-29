"""Builds app_data.json for the web app (app/index.html): every place (rated pool + new reference places) with each
person's score, a per-place 'why' breakdown from the ridge weights, plus validation, clusters, topics and 3D data.
Run after model.py, recs.py, refscore.py, build_viz_data.py and viz3d_data.py.
--private keeps review sentence text in the 3D galaxy (local use only; never commit that file)."""
import json, os, re, sys
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
import numpy as np, pandas as pd
PRIV = '--private' in sys.argv
O = 'out'
v = json.load(open(f'{O}/viz_data.json')); g = json.load(open(f'{O}/viz3d_data.json'))
RST = pd.read_csv('restaurants.csv').set_index('k')
F = pd.read_csv(f'{O}/features_v4.csv', index_col='k')
cols = [c for c in F if c.startswith('net_')] + [c for c in F if c.startswith('talk_')]
Z = (F[cols] - F[cols].mean()) / F[cols].std().replace(0, 1)
coef = {w: pd.Series(c)[cols] for w, c in g['coef'].items()}

def why(zrow):
    """top 3 features pushing the prediction up, per person: weight x standardized value"""
    out = {}
    for w, c in coef.items():
        contrib = (c * zrow[cols].values.astype(float)).sort_values(ascending=False)
        out[w] = [[k, round(float(x), 4)] for k, x in contrib.head(3).items() if x > 0]
    return out

# Yelp stars for the pool come from the original search cards (shown only as a crowd check, never a model input)
stars = {}
m4 = json.load(open(f'{DATA}/lists/m4_full.json')); slugs = json.load(open(f'{DATA}/lists/final_slugs.json'))
for k, slug in slugs.items():
    for c in (m4.get(k) or {}).get('cands', []):
        if c['slug'] == slug:
            mm = re.search(re.escape(c['title']) + r'\s*([\d.]+)\s*\((\d[\d,]*) reviews?\)', c['ctx'])
            if mm: stars[k] = float(mm.group(1))
            break
pool = []
for p in g['places']:
    k = p['k']
    r = dict(k=k, name=p['name'], fam=p['fam'], cl=p['cl'], x=p['x'], y=p['y'], z=p['z'], new=False,
             hood=str(RST.hood.get(k, '') or '') if not pd.isna(RST.hood.get(k, '')) else '',
             price=None if pd.isna(RST.price.get(k)) else int(RST.price.get(k)), stars=stars.get(k))
    for w in coef:
        r[w] = p[w]; r[w + '_pred'] = p[w + '_pred']
    r['why'] = why(Z.loc[k])
    pool.append(r)
ref = []
if os.path.exists(f'{O}/ref_predictions.csv'):
    RP = pd.read_csv(f'{O}/ref_predictions.csv', index_col=0); RZ = pd.read_csv(f'{O}/ref_features_z.csv', index_col=0)
    cand = json.load(open(f'{DATA}/ref_cand.json'))
    for k in RP.index:
        c = cand.get(k, {})
        r = dict(k=k, name=RP.title[k], new=True, hood=(c.get('hood') or '').split(',')[0], price=c.get('price'), stars=c.get('stars'), nrev=c.get('nrev'),
                 x=round(float(RZ.loc[k, 'net_flavor']), 3), y=round(float(RZ.loc[k, 'net_service']), 3), z=round(float(RZ.loc[k, 'talk_wait']), 3))
        for w in coef:
            r[w] = None; r[w + '_pred'] = round(float(RP[w][k]), 3)
        r['why'] = why(RZ.loc[k])
        ref.append(r)
gal = dict(g['galaxy'])
if not PRIV: gal['text'] = []
out = dict(V=v['V'], A=v['A'], topics=v['topics'], clusters=v['clusters'], stats=v['stats'], choice=v['choice'], refsum=v.get('refsum'),
           coef={w: {k: float(x) for k, x in c.items()} for w, c in coef.items()}, places=pool + ref, surf=g['surf'], galaxy=gal,
           ou=json.load(open(f'{O}/opinion_unit_test.json')), freeze=json.load(open('topic_model_v4/README.json'))['check'])
fn = f'{O}/app_data{"_private" if PRIV else ""}.json'
json.dump(out, open(fn, 'w'), separators=(',', ':'))
print(len(pool), 'pool', len(ref), 'new', sum(1 for p in pool if p['stars']), 'with stars', os.path.getsize(fn) // 1024, 'KB')
