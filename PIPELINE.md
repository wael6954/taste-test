# Pipeline review guide

A walkthrough of every stage for reviewing the project together. Each stage lists what it does, its inputs and outputs, the numbers worth sanity-checking, the decision made there, and what is still open. The web app (`app/index.html`, Pipeline tab) shows the same guide with a checkbox per stage.

```
Beli lists ─► percentiles ─► Yelp match ─► review pull ─► sentences + embeddings + sentiment
                                                                 │
                         topics (pos / neu / neg) ─► 12 aspects ─► features per restaurant
                                                                 │
            ridge model per person ◄─────────────────────────────┤──► clusters (summary)
                    │                                            │
      group rules ─► recommendations          frozen topics ─► new places scored
```

## 1. Beli lists → percentiles

**Where:** `pipeline/lists, ratings.py` · **Headline:** 151 + 110 places, 59 shared

Screenshots of both Beli lists are OCR'd and cleaned. Each person's rank becomes a within-person percentile, so a harsh and a generous scorer are comparable.

**In → out:** Beli screenshots → `lists_final.json` → `ratings_all.csv` (person, place, percentile), `restaurants.csv` (name, area, price, cuisine family)

**Check:**

- Wael 151 places, Z 110; 59 on both lists
- Spot-check five names per list against the app
- Chains with several locations are merged into one row (n_locs column)

**Decided:** Percentiles, not Beli's 0-10 score: the score is relative to each person's list anyway, and percentiles make two lists comparable.

**Open:** Beli also has want-to-try lists. Adding them as weak positives could help, but they are not ratings.

**Run:** `python lists/clean.py && python ratings.py`

## 2. Match to Yelp

**Where:** `browser/yelp_match.js, lists/match.py` · **Headline:** 196 of 202 matched

Each restaurant is searched on Yelp near its Beli area; candidates are scored on name similarity and area, and the best one is kept. Low-confidence matches were fixed by hand.

**In → out:** `restaurants.csv` → Yelp search cards (`m4_full.json`) → `final_slugs.json` (place → Yelp page)

**Check:**

- 196 of 202 places matched; 6 have no usable Yelp page
- Look at any match where the Yelp name differs a lot from the Beli name

**Decided:** Yelp over Google: Yelp pages can be paged by rating in the browser without an API key.

**Open:** Google reviews would add volume and more middling opinions. Needs an API key or a separate scraper.

**Run:** `browser/yelp_match.js in a yelp.ca tab: window.__matchAll(), then python lists/match.py`

## 3. Pull reviews

**Where:** `browser/yelp_reviews.js` · **Headline:** 5,818 reviews

For each matched page: the 35 highest-rated reviews plus 5 from the default order closest to 3 stars. Pulled in a visible browser tab with pauses between pages.

**In → out:** `final_slugs.json` → `beli_yelp_raw/` (one JSON per restaurant, kept outside git)

**Check:**

- 5,818 reviews for 195 places
- Places with fewer than 5 reviews are dropped later (177 remain)
- Re-run anything that came back empty: the tab has to stay visible or pages time out

**Decided:** 35 best + 5 average. Stars are kept only for after-the-fact checks, never as model input.

**Open:** Mostly 5-star text means few complaints (11% negative sentences). More average or low reviews would sharpen the complaint topics.

**Run:** `browser/yelp_reviews.js in a yelp.ca tab: window.__runPulls()`

## 4. Sentences, embeddings, sentiment

**Where:** `browser/embed.js` · **Headline:** 37,509 sentences

Reviews are split into sentences with the restaurant's own name masked. Each sentence gets a 768-number meaning vector (all-mpnet-base-v2) and a positive / neutral / negative label (RoBERTa sentiment), computed on the GPU in the browser.

**In → out:** raw reviews → `v4_meta.json` + `v4_emb_chunk_*.bin`, `v4_sent_chunk_*.bin`

**Check:**

- 37,509 sentences, every vector unit length (asserted on load)
- Sentiment mix: 60% positive, 29% neutral, 11% negative

**Decided:** Sentence splitting instead of LLM opinion units, for cost and reproducibility (tested in the Checks tab).

**Open:** Whether a larger, less positive sample makes LLM opinion units worth it.

**Run:** `browser/embed.js: window.__embedRun("pulls", "v4"), then python browser/collect_downloads.py`

## 5. Topics

**Where:** `topics.py, tags_manual.py` · **Headline:** 166 topics, 12 aspects

Positive, neutral and negative sentences are clustered separately (UMAP then HDBSCAN), so "great service" and "slow service" become different topics. Settings are picked by how stable the topics are across random seeds. Each topic is hand-tagged with one of 12 aspects, a dish ("what"), or noise.

**In → out:** embeddings + sentiment → `sentences.csv`, `topics_tagged.csv`

**Check:**

- 166 usable topics; 36% of sentences are unassigned or noise
- Skim the topic table in the Taste tab: names should read as one idea each

**Decided:** The clustering found 180 topics. Hand-tagging them took one pass, and 14 turned out to be talk about the reviews themselves, so 166 were kept. The tags are what make the model readable.

**Open:** A few aspects (location, occasion) have thin topics and may be merging unrelated things.

**Run:** `python topics.py && python tags_manual.py`

## 6. Features per restaurant

**Where:** `model.py` · **Headline:** 24 features

For every restaurant and aspect: net sentiment (praise minus complaints, shrunk toward zero when there are few mentions) and talk rate (share of sentences about that aspect). Standardized across restaurants.

**In → out:** `sentences.csv` → `features_v4.csv`

**Check:**

- 177 restaurants with at least 5 reviews
- Food praise should be high for places you both rate highly; check a couple in the 3D view

**Decided:** Counting dish sentences as food praise was tried and dropped: it caught more opinions but predicted worse.

**Open:** Talk rates depend on how many reviews a place has; a place with 12 reviews is noisier than one with 40.

**Run:** `python model.py`

## 7. Models and clusters

**Where:** `model.py, permtest.py` · **Headline:** Spearman 0.26 / 0.38

Seven methods were compared on held-out places. The winner is a ridge regression per person on the 24 features. Overlapping clusters (GMM, fuzzy c-means) are kept as a readable summary of kinds of restaurant, not as the predictor.

**In → out:** features + percentiles → `pred_*.csv`, `ridge_coef_*.csv`, `clusters_v4.csv`, `validation_v4.json`

**Check:**

- Wael 0.26 vs random 0.17; Z 0.38 vs random 0.20
- Permutation test: p < 0.01 for both
- Cuisine alone does not predict either list (baseline near zero)

**Decided:** Ridge on aspects + talk rate. Clusters looked nice but predicted barely better than chance.

**Open:** Seven methods tried on one dataset. More people and more lists are the real test.

**Run:** `python model.py && python permtest.py`

## 8. Group recommendations

**Where:** `recs.py` · **Headline:** 5 combining rules

Each person's score is their own percentile where they have been and the model's prediction elsewhere. Scores are combined with a group rule: average, least misery, average without misery, multiplicative, Borda.

**In → out:** `pred_*.csv` → `recs_*.csv`

**Check:**

- Top picks for both should include places one of you loves and the other has not tried
- Least misery and average-without-misery should rarely surface a place either of you ranks low

**Decided:** Average without misery (drop anything under 35 for either person) as the default for picking together.

**Open:** The 35 cut-off is a guess. Worth tuning after a few real dinners.

**Run:** `python recs.py`

## 9. New places

**Where:** `freeze.py, browser/reference.js, refscore.py` · **Headline:** 326 new places scored

Restaurants neither of you has rated are pulled from Yelp searches in the areas you actually go (20 reviews each). Their sentences are mapped onto the frozen topics by nearest neighbours, turned into the same features, and scored with each person's model.

**In → out:** Yelp search cards → `ref_cand.json` → `ref_meta.json` + chunks → `ref_predictions.csv`, `refrecs_*.csv`

**Check:**

- Frozen topics agree with the original on 98% of held-out sentences
- 326 places with at least 5 reviews scored
- Crowd check: top-20 picks average 4.25★ vs 4.17★ overall; prediction vs stars ρ = 0.103

**Decided:** Freeze the topic model so new places never shift the features of rated ones. Talk rates are rescaled for the slightly lower assignment rate.

**Open:** New places have 20 reviews, rated ones about 30. Fewer reviews means noisier features; the scores for new places are less certain.

**Run:** `window.__discover(); window.__runRef(); window.__embedRun("ref_pulls", "ref"); python freeze.py && python refscore.py ref`

## 10. App

**Where:** `app_data.py, build_app.py` · **Headline:** this app

Collects every output into one data file and builds this app. The public build drops review text.

**In → out:** all outputs → `app/index.html`

**Check:**

- No review sentences in anything committed (the build script strips them)
- Open the app on a phone too

**Decided:** One self-contained HTML file per page, data inlined, so it opens from disk or as a hosted page.

**Open:** Add a third person: drop their list in and rerun from stage 1.

**Run:** `python app_data.py && python build_app.py`
