"""Step 1-3: per-person percentiles, restaurant table (cuisine family, price) for the v4 pool."""
import json, re, os
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
import numpy as np, pandas as pd

D = os.path.dirname(os.path.abspath(__file__))
OCR = f'{DATA}/lists'
places = json.load(open(f'{OCR}/places.json'))
raw = json.load(open(f'{OCR}/lists_raw.json'))
final = json.load(open(f'{OCR}/lists_final.json'))
slugs = json.load(open(f'{OCR}/final_slugs.json'))

FAM = [  # first match wins
    ('sweets_bakery', r'ice cream|bakery|dessert|gelato|bubble tea|juice|donut|cheesecake'),
    ('cafe_brunch', r'brunch|breakfast|cafe|coffee|diner'),
    ('middle_eastern', r'lebanese|middle eastern|shawarma|arabic|syrian|iraqi|egyptian|jordanian|saudi|yemeni|persian|afghan|falafel|kebab|turkish|mediterranean|greek|uyghur'),
    ('south_asian', r'indian|pakistani|sri lankan|nepal|tibetan'),
    ('japanese', r'japanese|sushi|ramen|izakaya|udon|poke'),
    ('korean', r'korean'),
    ('chinese', r'chinese|dumpling|dim sum|sichuan|hot pot|cantonese|taiwanese|noodles'),
    ('se_asian', r'vietnamese|thai|laotian|pho|malaysian|filipino'),
    ('mexican_latin', r'mexican|tex-mex|burrito|taqueria|tacos|caribbean|jamaican|portuguese|peruvian|latin'),
    ('italian_pizza', r'italian|pizza|roman'),
    ('fried_chicken_wings', r'fried chicken|chicken|wings'),
    ('burgers_fast', r'burgers|fast food|hot dogs|fast casual|food court'),
    ('bar_pub', r'pub|bar|gastropub|british|irish|sports bar'),
    ('sandwich_deli', r'sandwich|deli|delicatessen|jewish|grocery|healthy|emporium|market'),
    ('steak_grill_bbq', r'steak|barbecue|grill|meat|southern|cajun'),
    ('american_other', r'american|fusion|seafood|canadian|californian|international|new zealand|south african|french|swedish|quebecois|asian'),
]
def family(tags, name):
    s = (tags + ' | ' + name).lower()
    for f, rx in FAM:
        if re.search(rx, s): return f
    return 'other'

def key(s):  # same normalization used to build places.json
    s = str(s).lower()
    return s

# map each (person, rank) -> place key
rk = {}
for p in places:
    for who, ranks in p['who'].items():
        for r in ranks: rk[(who, r)] = p['k']

cu = {}
for who in ['wael', 'zed']:
    for x in raw[who]:
        k = rk.get((who, x['rank']))
        if k and x.get('cu'): cu.setdefault(k, []).append(x['cu'])

rows = []
for p in places:
    k = p['k']; c = ' '.join(cu.get(k, []))
    pm = re.findall(r'(\${1,4})', c); price = len(max(pm, key=len)) if pm else np.nan
    tags = re.sub(r'\${1,4}|[»«+·]|View Map|Suggest cuisines\?|\(\)', ' ', c)
    rows.append(dict(k=k, name=p['name'], hood=p['hood'], slug=slugs.get(k), price=price,
                     tags=re.sub(r'\s+', ' ', tags).strip(), family=family(tags, p['name'])))
Rst = pd.DataFrame(rows)
Rst.to_csv(f'{D}/restaurants.csv', index=False)
print(Rst.family.value_counts().to_dict())
print('no slug', Rst.slug.isna().sum(), 'no price', Rst.price.isna().sum())

# percentiles: rank order within each person's GTA pool list (rank 1 = best)
rat = []
for who in ['wael', 'zed']:
    lst = [(r, k) for (w, r), k in rk.items() if w == who]
    lst.sort()
    n = len(lst)
    for i, (r, k) in enumerate(lst):
        rat.append(dict(person=who, k=k, rank=r, pct=1 - (i + 0.5) / n))
R = pd.DataFrame(rat).groupby(['person', 'k'], as_index=False).agg(pct=('pct', 'mean'), rank=('rank', 'min'), n_locs=('rank', 'size'))
R.to_csv(f'{D}/ratings_all.csv', index=False)
print(R.groupby('person').size().to_dict(), 'both', (R.groupby('k').size() == 2).sum())
