"""Re-parse stars, review count and area for the reference candidates from each search card's text.
The first parse in the browser sometimes took the previous card's numbers (e.g. Gusto 101 got Public Gardens' 4.2 / 54),
or read a name ending in digits as part of the rating (Petros82 -> 824.5).
When the card text is another listing's, stars, count and area are cleared (unknown) rather than kept wrong. Stars and counts are a check only, never a model input."""
import json, os, re, sys
DATA = os.environ.get('BELI_DATA', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data'))  # raw inputs; see data/README.md
fn = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'ref_cand.json')
c = json.load(open(fn)); changed = []
STOP = r'(?:\$|Closed|Open|"|\d+\.\s)'
for k, x in c.items():
    ctx, t = re.sub(r'\s+', ' ', x.get('ctx', '')), re.sub(r'\s+', ' ', x['title'])
    i = ctx.find(t)
    if i < 0:
        # the card text belongs to a different listing, so none of its numbers can be trusted
        if x.get('stars') is not None:
            changed.append((x['title'], (x['stars'], x['nrev'], x.get('hood')), (None, None, None)))
            x.update(stars=None, nrev=None, hood=None, card_mismatch=True)
        continue
    m = re.match(r'\s*([1-5]\.\d)\s*\((?:([\d.,]+)(k?)\s*r)?', ctx[i + len(t):])
    if not m: continue
    stars = float(m.group(1)); nrev = x['nrev']
    if m.group(2):
        n = float(m.group(2).replace(',', '')); nrev = int(round(n * 1000)) if m.group(3) else int(n)
    rest = ctx[i + len(t) + m.end():]
    h = re.match(r'\w*\)\s*(.*?)' + STOP, rest, re.S) if m.group(2) else None
    hood = h.group(1).strip() if h and h.group(1).strip() else x.get('hood')
    if (stars, nrev, hood) != (x['stars'], x['nrev'], x.get('hood')):
        changed.append((t, (x['stars'], x['nrev'], x.get('hood')), (stars, nrev, hood)))
        x.update(stars=stars, nrev=nrev, hood=hood)
json.dump(c, open(fn, 'w'))
print(len(changed), 'fixed')
for ch in changed: print(ch)
