import json, re, sys
from difflib import SequenceMatcher
m = json.load(open(sys.argv[1]))
def norm(s): return re.sub(r'[^a-z0-9 ]', '', re.sub(r'\(.*?\)', '', s.lower().replace('’', "'").replace('&', ' and '))).strip()
HOOD_ALIAS = {'church-wellesley': ['church-wellesley', 'church wellesley', 'village'], 'downtown yonge': ['downtown core', 'downtown yonge', 'yonge', 'the village'],
              'fashion district': ['fashion district', 'queen street west', 'entertainment district', 'chinatown', 'downtown core'],
              'grange park': ['grange park', 'chinatown', 'kensington', 'baldwin'], 'yonge-bay corridor': ['downtown core', 'financial district', 'yonge'],
              'bay-cloverhill': ['bay', 'church-wellesley', 'yorkville', 'downtown core', 'discovery'], 'wellington place': ['entertainment district', 'king west', 'fashion district'],
              'queen street west': ['queen street west', 'trinity bellwoods', 'west queen west', 'fashion district', 'chinatown', 'kensington'],
              'downtown yonge east': ['downtown core', 'church-wellesley', 'yonge', 'garden district'], 'harbord village': ['harbord', 'the annex', 'university'],
              'bloor annex': ['annex', 'koreatown', 'seaton'], 'mirvish village': ['koreatown', 'annex', 'seaton'], 'koreatown': ['koreatown', 'annex', 'seaton'],
              'mississauga': ['mississauga'], 'erin mills': ['mississauga'], 'wexford heights': ['scarborough'], 'liberty village': ['liberty village', 'king west', 'niagara'],
              'kensington market': ['kensington', 'chinatown'], 'chinatown': ['chinatown', 'kensington'], 'financial district': ['financial district', 'downtown core'],
              'yorkville': ['yorkville'], 'beaconsfield village': ['beaconsfield', 'little portugal', 'west queen west', 'ossington'], 'baldwin village': ['baldwin', 'grange', 'chinatown'],
              'university': ['university', 'the annex', 'discovery'], 'st. lawrence': ['st. lawrence', 'old toronto', 'st lawrence'], 'cabbagetown': ['cabbagetown', 'regent'],
              'cabbagetown south': ['cabbagetown', 'regent', 'church-wellesley'], 'west queen west': ['west queen west', 'trinity bellwoods'], 'trinity-bellwoods': ['trinity bellwoods', 'queen street west'],
              'palmerston': ['palmerston', 'little italy', 'annex'], 'north toronto': ['north toronto', 'yonge and eglinton', 'midtown'], 'yorkdale': ['yorkdale', 'north york'],
              'etobicoke city centre': ['etobicoke'], 'east willowdale': ['willowdale', 'north york'], 'bayview village': ['bayview', 'north york'], 'thornhill': ['thornhill', 'vaughan'],
              'oakville': ['oakville'], 'cityplace': ['cityplace', 'entertainment district', 'fort york'], 'harbourfront-cityplace': ['harbourfront', 'cityplace', 'entertainment'],
              'entertainment district': ['entertainment district', 'downtown core'], 'upper jarvis': ['church-wellesley', 'downtown core', 'garden'],
              'lower don lands': ['port lands', 'distillery', 'portlands'], 'south eglinton-davisville': ['davisville', 'yonge and eglinton', 'midtown'],
              'little tibet': ['parkdale'], 'south core': ['south core', 'harbourfront', 'entertainment'], 'discovery district': ['discovery', 'downtown core', 'university'],
              'fort york-liberty village': ['liberty village', 'fort york', 'king west'], 'yonge-doris': ['north york', 'willowdale'], "ward's island": ['toronto islands', 'ward'],
              'hillcrest village': ['north york', 'hillcrest'], 'bloordale village': ['bloordale', 'bloor west', 'dufferin grove']}
out = {}
for k, v in m.items():
    q = v['q']; name = q[1]; hood = q[2].split(',')[0].lower()
    cands = v.get('cands') or []
    best = None
    for c in cands:
        t = c['title']; s = SequenceMatcher(None, norm(name), norm(t)).ratio()
        if norm(t) and (norm(t) in norm(name) or norm(name).split(' - ')[0] in norm(t)): s = max(s, 0.85)
        mm = re.search(re.escape(t) + r'\s*([\d.]+)\s*\((\d[\d,]*) reviews?\)(.*?)(?:\$|Open|Closed|"|$)', c['ctx'])
        rev = int(mm.group(2).replace(',', '')) if mm else None; nh = (mm.group(3).strip() if mm else '')
        al = HOOD_ALIAS.get(hood, [hood]); hm = any(a in nh.lower() for a in al) if nh else False
        score = s + (0.2 if hm else 0)
        if best is None or score > best['score']: best = dict(slug=c['slug'], title=t, sim=round(s, 2), hood=nh, hood_ok=hm, reviews=rev, score=round(score, 2))
    out[k] = dict(name=name, want=q[2], err=v.get('err'), best=best, cands=[(c['slug'], c['title']) for c in cands])
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
ok = [k for k, v in out.items() if v['best'] and v['best']['sim'] >= 0.8 and v['best']['hood_ok']]
mid = [k for k, v in out.items() if v['best'] and k not in ok and v['best']['sim'] >= 0.6]
bad = [k for k in out if k not in ok and k not in mid]
print('confident', len(ok), 'check', len(mid), 'bad', len(bad))
for k in mid + bad:
    v = out[k]; b = v['best'] or {}
    print(f"{k:32s} | {v['name'][:34]:34s} @ {v['want'][:28]:28s} -> {b.get('title','-')[:32]:32s} | {b.get('hood','')[:24]:24s} sim {b.get('sim')} rev {b.get('reviews')} {v['err'] or ''}")
