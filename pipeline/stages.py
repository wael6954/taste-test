"""Single source for the pipeline review guide: writes out/stages.json (used by the web app) and PIPELINE.md.
Numbers are read from the pipeline outputs so the guide stays in step with the latest run.
Usage: python stages.py [path/to/PIPELINE.md]"""
import json, os, sys
import pandas as pd
O = 'out'
J = lambda f: json.load(open(f'{O}/{f}'))
val, perm, ref, ou = J('validation_v4.json'), J('permtest_ridge_talk.json'), J('ref_summary.json'), J('opinion_unit_test.json')
frz = json.load(open('topic_model_v4/README.json'))['check']
v = json.load(open(f'{O}/viz_data.json')); st = v['stats']; ch = v['choice']
R = pd.read_csv('ratings_all.csv'); n_w, n_z = (R.person == 'wael').sum(), (R.person == 'zed').sum()
shared = len(set(R.k[R.person == 'wael']) & set(R.k[R.person == 'zed']))
T = pd.read_csv(f'{O}/topics_tagged.csv'); n_topics = int((T.tag != 'noise').sum())
cc = ref['crowd_check'].get('wael+zed|average', {})
sp = lambda w: ch[w]['held_out']['spearman']; nul = lambda w: v['V'][w]['null_sp']

S = [
 dict(id='lists', name='Beli lists → percentiles', where='pipeline/lists, ratings.py', key=f'{n_w} + {n_z} places, {shared} shared',
      what='Screenshots of both Beli lists are OCR\'d and cleaned. Each person\'s rank becomes a within-person percentile, so a harsh and a generous scorer are comparable.',
      io='Beli screenshots → <code>lists_final.json</code> → <code>ratings_all.csv</code> (person, place, percentile), <code>restaurants.csv</code> (name, area, price, cuisine family)',
      check=[f'Wael {n_w} places, Z {n_z}; {shared} on both lists', 'Spot-check five names per list against the app', 'Chains with several locations are merged into one row (n_locs column)'],
      decided='Percentiles, not Beli\'s 0-10 score: the score is relative to each person\'s list anyway, and percentiles make two lists comparable.',
      open='Beli also has want-to-try lists. Adding them as weak positives could help, but they are not ratings.',
      run='python lists/clean.py && python ratings.py'),
 dict(id='match', name='Match to Yelp', where='browser/yelp_match.js, lists/match.py', key='196 of 202 matched',
      what='Each restaurant is searched on Yelp near its Beli area; candidates are scored on name similarity and area, and the best one is kept. Low-confidence matches were fixed by hand.',
      io='<code>restaurants.csv</code> → Yelp search cards (<code>m4_full.json</code>) → <code>final_slugs.json</code> (place → Yelp page)',
      check=['196 of 202 places matched; 6 have no usable Yelp page', 'Look at any match where the Yelp name differs a lot from the Beli name'],
      decided='Yelp over Google: Yelp pages can be paged by rating in the browser without an API key.',
      open='Google reviews would add volume and more middling opinions. Needs an API key or a separate scraper.',
      run='browser/yelp_match.js in a yelp.ca tab: window.__matchAll(), then python lists/match.py'),
 dict(id='reviews', name='Pull reviews', where='browser/yelp_reviews.js', key=f'{st["reviews"]:,} reviews',
      what='For each matched page: the 35 highest-rated reviews plus 5 from the default order closest to 3 stars. Pulled in a visible browser tab with pauses between pages.',
      io='<code>final_slugs.json</code> → <code>beli_yelp_raw/</code> (one JSON per restaurant, kept outside git)',
      check=[f'{st["reviews"]:,} reviews for {st["restaurants"]} places', 'Places with fewer than 5 reviews are dropped later (177 remain)', 'Re-run anything that came back empty: the tab has to stay visible or pages time out'],
      decided='35 best + 5 average. Stars are kept only for after-the-fact checks, never as model input.',
      open='Mostly 5-star text means few complaints (11% negative sentences). More average or low reviews would sharpen the complaint topics.',
      run='browser/yelp_reviews.js in a yelp.ca tab: window.__runPulls()'),
 dict(id='embed', name='Sentences, embeddings, sentiment', where='browser/embed.js', key=f'{st["sentences"]:,} sentences',
      what='Reviews are split into sentences with the restaurant\'s own name masked. Each sentence gets a 768-number meaning vector (all-mpnet-base-v2) and a positive / neutral / negative label (RoBERTa sentiment), computed on the GPU in the browser.',
      io='raw reviews → <code>v4_meta.json</code> + <code>v4_emb_chunk_*.bin</code>, <code>v4_sent_chunk_*.bin</code>',
      check=[f'{st["sentences"]:,} sentences, every vector unit length (asserted on load)', f'Sentiment mix: {round(st["pol"]["pos"]*100)}% positive, {round(st["pol"]["neu"]*100)}% neutral, {round(st["pol"]["neg"]*100)}% negative'],
      decided='Sentence splitting instead of LLM opinion units, for cost and reproducibility (tested in the Checks tab).',
      open='Whether a larger, less positive sample makes LLM opinion units worth it.',
      run='browser/embed.js: window.__embedRun("pulls", "v4"), then python browser/collect_downloads.py'),
 dict(id='topics', name='Topics', where='topics.py, tags_manual.py', key=f'{n_topics} topics, 12 aspects',
      what='Positive, neutral and negative sentences are clustered separately (UMAP then HDBSCAN), so "great service" and "slow service" become different topics. Settings are picked by how stable the topics are across random seeds. Each topic is hand-tagged with one of 12 aspects, a dish ("what"), or noise.',
      io='embeddings + sentiment → <code>sentences.csv</code>, <code>topics_tagged.csv</code>',
      check=[f'{n_topics} usable topics; {round(st["noise_share"]*100)}% of sentences are unassigned or noise', 'Skim the topic table in the Taste tab: names should read as one idea each'],
      decided='The clustering found 180 topics. Hand-tagging them took one pass, and 14 turned out to be talk about the reviews themselves, so 166 were kept. The tags are what make the model readable.',
      open='A few aspects (location, occasion) have thin topics and may be merging unrelated things.',
      run='python topics.py && python tags_manual.py'),
 dict(id='features', name='Features per restaurant', where='model.py', key='24 features',
      what='For every restaurant and aspect: net sentiment (praise minus complaints, shrunk toward zero when there are few mentions) and talk rate (share of sentences about that aspect). Standardized across restaurants.',
      io='<code>sentences.csv</code> → <code>features_v4.csv</code>',
      check=['177 restaurants with at least 5 reviews', 'Food praise should be high for places you both rate highly; check a couple in the 3D view'],
      decided='Counting dish sentences as food praise was tried and dropped: it caught more opinions but predicted worse.',
      open='Talk rates depend on how many reviews a place has; a place with 12 reviews is noisier than one with 40.',
      run='python model.py'),
 dict(id='model', name='Models and clusters', where='model.py, permtest.py', key=f'Spearman {sp("wael"):.2f} / {sp("zed"):.2f}',
      what='Seven methods were compared on held-out places. The winner is a ridge regression per person on the 24 features. Overlapping clusters (GMM, fuzzy c-means) are kept as a readable summary of kinds of restaurant, not as the predictor.',
      io='features + percentiles → <code>pred_*.csv</code>, <code>ridge_coef_*.csv</code>, <code>clusters_v4.csv</code>, <code>validation_v4.json</code>',
      check=[f'Wael {sp("wael"):.2f} vs random {nul("wael"):.2f}; Z {sp("zed"):.2f} vs random {nul("zed"):.2f}', 'Permutation test: p < 0.01 for both', 'Cuisine alone does not predict either list (baseline near zero)'],
      decided='Ridge on aspects + talk rate. Clusters looked nice but predicted barely better than chance.',
      open='Seven methods tried on one dataset. More people and more lists are the real test.',
      run='python model.py && python permtest.py'),
 dict(id='recs', name='Group recommendations', where='recs.py', key='5 combining rules',
      what='Each person\'s score is their own percentile where they have been and the model\'s prediction elsewhere. Scores are combined with a group rule: average, least misery, average without misery, multiplicative, Borda.',
      io='<code>pred_*.csv</code> → <code>recs_*.csv</code>',
      check=['Top picks for both should include places one of you loves and the other has not tried', 'Least misery and average-without-misery should rarely surface a place either of you ranks low'],
      decided='Average without misery (drop anything under 35 for either person) as the default for picking together.',
      open='The 35 cut-off is a guess. Worth tuning after a few real dinners.',
      run='python recs.py'),
 dict(id='ref', name='New places', where='freeze.py, browser/reference.js, refscore.py', key=f'{ref["n_ref"]} new places scored',
      what='Restaurants neither of you has rated are pulled from Yelp searches in the areas you actually go (20 reviews each). Their sentences are mapped onto the frozen topics by nearest neighbours, turned into the same features, and scored with each person\'s model.',
      io='Yelp search cards → <code>ref_cand.json</code> → <code>ref_meta.json</code> + chunks → <code>ref_predictions.csv</code>, <code>refrecs_*.csv</code>',
      check=[f'Frozen topics agree with the original on {round(frz["same_topic_when_both_assigned"]*100)}% of held-out sentences', f'{ref["n_ref"]} places with at least 5 reviews scored', f'Crowd check: top-20 picks average {cc.get("top20_mean_stars", "?")}★ vs {cc.get("ref_mean_stars", "?")}★ overall; prediction vs stars ρ = {cc.get("spearman_pred_vs_stars", "?")}'],
      decided='Freeze the topic model so new places never shift the features of rated ones. Talk rates are rescaled for the slightly lower assignment rate.',
      open='New places have 20 reviews, rated ones about 30. Fewer reviews means noisier features; the scores for new places are less certain.',
      run='window.__discover(); window.__runRef(); window.__embedRun("ref_pulls", "ref"); python freeze.py && python refscore.py ref'),
 dict(id='viz', name='App', where='app_data.py, build_app.py', key='this app',
      what='Collects every output into one data file and builds this app. The public build drops review text.',
      io='all outputs → <code>app/index.html</code>',
      check=['No review sentences in anything committed (the build script strips them)', 'Open the app on a phone too'],
      decided='One self-contained HTML file per page, data inlined, so it opens from disk or as a hosted page.',
      open='Add a third person: drop their list in and rerun from stage 1.',
      run='python app_data.py && python build_app.py'),
]
json.dump(S, open(f'{O}/stages.json', 'w'), indent=1)

if len(sys.argv) > 1:
    import re
    md = lambda s: re.sub(r'<code>(.*?)</code>', r'`\1`', s).replace('&lt;', '<').replace('&gt;', '>')
    L = ['# Pipeline review guide', '',
         'A walkthrough of every stage for reviewing the project together. Each stage lists what it does, its inputs and outputs, the numbers worth sanity-checking, the decision made there, and what is still open. The web app (`app/index.html`, Pipeline tab) shows the same guide with a checkbox per stage.', '',
         '```', 'Beli lists ─► percentiles ─► Yelp match ─► review pull ─► sentences + embeddings + sentiment',
         '                                                                 │',
         '                         topics (pos / neu / neg) ─► 12 aspects ─► features per restaurant',
         '                                                                 │',
         '            ridge model per person ◄─────────────────────────────┤──► clusters (summary)',
         '                    │                                            │',
         '      group rules ─► recommendations          frozen topics ─► new places scored',
         '```', '']
    for i, s in enumerate(S, 1):
        L += [f'## {i}. {s["name"]}', '', f'**Where:** `{s["where"]}` · **Headline:** {s["key"]}', '', md(s['what']), '',
              f'**In → out:** {md(s["io"])}', '', '**Check:**', ''] + [f'- {md(c)}' for c in s['check']] + ['',
              f'**Decided:** {md(s["decided"])}', '', f'**Open:** {md(s["open"])}', '', f'**Run:** `{s["run"]}`', '']
    open(sys.argv[1], 'w').write('\n'.join(L))
print(len(S), 'stages')
