"""v4 stage A2: first-pass aspect tag per topic from its top words + examples (keyword scoring).
Every tag is then reviewed by hand in tags_override.json before features are built."""
import os, re, json
import pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'
T = pd.read_csv(f'{OUT}/topics_raw.csv')
KW = {
    'service': r'\b(service|staff|server|waiter|waitress|friendly|attentive|rude|owner|manager|hospitality|welcom|host|bartender|employee|cashier|customer)\w*',
    'wait': r'\b(wait|line|lineup|queue|busy|reservation|minutes|slow|fast|quick|seated|hour)\w*',
    'ambience': r'\b(ambiance|ambience|atmosphere|decor|vibe|music|cozy|interior|loud|noise|seating|patio|space|clean|dirty|lighting|view|aesthetic)\w*',
    'value': r'\b(price|priced|expensive|cheap|worth|value|affordable|overpriced|cost|deal|money|\$)\w*',
    'portions': r'\b(portion|size|huge|generous|filling|small|amount|full|stuffed|big|large)\w*',
    'flavor': r'\b(flavou?r|season|spic|salt|bland|sweet|savou?ry|taste|tasty|delicious|sauce|rich|tender|crisp|juicy|fresh)\w*',
    'quality': r'\b(quality|fresh|ingredient|authentic|homemade|cooked|undercooked|overcooked|dry|soggy|cold|greasy|stale)\w*',
    'location': r'\b(location|located|downtown|parking|street|area|neighbou?rhood|walk|subway|campus|mall|close|nearby|find)\w*',
    'logistics': r'\b(order|delivery|takeout|take-out|pickup|app|uber|online|cash|card|tip|hours|open|closed|bathroom|washroom)\w*',
    'menu': r'\b(menu|option|variety|selection|vegetarian|vegan|choice|halal|gluten)\w*',
    'occasion': r'\b(date|birthday|friends|family|group|celebrat|kids|lunch|brunch|dinner|night|weekend|study|work|tourist|visit|trip|first time)\w*',
    'overall': r'\b(best|recommend|favou?rite|amazing|great|love|back|again|disappoint|experience|overall|gem|worst|never)\w*',
}
rows = []
for _, t in T.iterrows():
    tw = t.top_words; ex = t.examples.lower()
    sc = {a: 3 * len(re.findall(rx, tw)) + len(re.findall(rx, ex)) for a, rx in KW.items()}
    a, s = max(sc.items(), key=lambda x: x[1])
    second = sorted(sc.values())[-2]
    # dish-identity topics: top words are mostly nouns of food items and no aspect wins clearly
    tag = a if s >= 4 and s >= second + 2 else 'what'
    rows.append(dict(topic_id=t.topic_id, polarity=t.polarity, size=t['size'], auto_tag=tag, score=s, top_words=tw, ex=t.examples[:220]))
R = pd.DataFrame(rows); R.to_csv(f'{OUT}/topics_autotag.csv', index=False)
print(R.groupby(['auto_tag', 'polarity']).size().unstack(fill_value=0))
