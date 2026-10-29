# Beli Taste Profile and Restaurant Recommender

## Goal

Recommend restaurants to any group of people (one person, two, or any number N) based on their own tastes. The system works for anyone who has a Beli list, not only a fixed set of users.

- **Input:** each person's Beli list (personal scores only).
- **Predictor:** clusters of restaurants with common features. A restaurant is recommended when it falls in, or close to, the clusters a person scores highly.
- **Output:** a ranked list for each person, and a ranked list for whichever group is going out together.
- **Personal scores only:** crowd scores (Beli global average, friends' average, Yelp or Google stars) are never inputs. They are used afterwards as a check.
- **Overlapping clusters:** a restaurant can belong to several clusters at once (one to many), with a membership strength in each.
- **Person-agnostic:** nothing in the pipeline is tuned to a specific person. Adding, removing or swapping people means loading their lists and rerunning only the person-level steps (taste profile and scoring).

## Methodology

### 1. Personal ratings

- Each person's Beli list gives their score (0 to 10), rank, price, cuisine and location for every place they have been.
- Scores are converted to a percentile within each person's own list. This removes differences in how harshly each person scores and makes everyone's lists comparable.
- Different locations of the same chain are treated as one restaurant with one averaged score.

### 2. Shared restaurant pool

- All participants' restaurants are pooled into one table with a shared restaurant ID.
- Features and clusters are built on the pooled set, so every person's taste profile is expressed in the same clusters.

### 3. Review corpus from Yelp and Google Maps

Yelp and Google Maps reviews are only used to build the features. Their star ratings are not used.

- For each restaurant, pull review text from both Yelp and Google Maps and pool it into one corpus per restaurant.
- Set a minimum review count per restaurant so features are not built from two or three reviews.
- Split each review into **opinion units**: short statements that each cover one aspect, with the excerpt that supports it and a sentiment score from 1 (very negative) to 10 (very positive). For example, "the broth was rich but the wait was 40 minutes" becomes two units: broth (positive) and wait (negative).
- Opinion units are extracted by an LLM with a fixed prompt and a few worked examples. Sentence splitting is the fallback if LLM extraction is too slow or costly.
- General remarks with no aspect ("great place, will be back") are dropped.

### 4. Review-defined features

The features come from what reviewers actually talk about, not from a hand-picked list.

- **Embed** every opinion unit (aspect label plus excerpt) with a sentence embedding model, so units with similar meaning sit close together.
- **Find topics** by grouping the embeddings (BERTopic style). Each group is one topic, such as "long lines and waiting", "studying with a laptop", "huge portions", "spicy broth".
- **Split by sentiment:** cluster positive units (sentiment 6 and up) and negative units (5 and below) separately, so each topic exists as a praised and a criticized version ("great service" and "bad service" are different features). In published work on Yelp restaurant reviews, this split was the change that made topics carry quality information, not just place type.
- **Choose the number of topics** by topic coherence and stability across reruns, then merge near-duplicate topics. Leave units that fit no topic unassigned (expect 15 to 30% of them).
- **Build each restaurant's feature vector** as the share of its opinion units in each sentiment-split topic.
- **Name topics afterwards** from their top words and most representative units, and map each one to the standard restaurant aspect categories from the SemEval aspect-based sentiment benchmark (food, drinks, service, ambience, location, restaurant overall, each crossed with general, prices, quality, style/options). The mapping is a check: if an area like service never appears, or one topic swallows everything, the topic model needs adjusting.
- **Structured features** kept alongside the topics: cuisine family and price level ($ to $$$$).

**Keeping it consistent across people:**

- Fit the topic model once on a large reference corpus (all restaurants in the pool, plus a broad sample of Toronto restaurants) and freeze it.
- Restaurants added by a new person are mapped onto the frozen topics, never refit, so features stay comparable no matter who is in the group.
- Refit only on purpose, and version the topic list each time.

### 5. Overlapping clustering

- Cluster all restaurants on the feature vectors with a soft method, so each restaurant gets a membership strength in every cluster.
- Clusters are fit on the reference corpus, not on one group's lists, so they do not change when the group changes.
- Name each cluster by the topics, cuisines and price that define it.

### 6. Taste profile per person

- For each person, compute how they rate each cluster: the average percentile of their places, weighted by each place's membership in that cluster.
- Clusters where a person has rated few places are pulled toward that person's overall average.

### 7. Recommendation

- **Per person:** an unknown restaurant's score is its cluster memberships weighted by that person's taste profile.
- **For the group:** combine the N personal scores. Rules to compare:
  - **Average:** the mean of the N scores (best overall satisfaction).
  - **Least misery:** the lowest of the N scores (nobody gets a place they would dislike).
  - **Trimmed average:** drop the lowest score, average the rest (for larger groups where one dissenter should not veto everything).
  - **Average without misery:** average the scores, but exclude any restaurant where someone falls below a threshold.
  - **Multiplicative:** multiply the scores, which punishes low scores without a hard cutoff.
  - **Borda count:** rank candidates within each person's list, give points by position, and sum the points.
- No single rule is best for every group. Research on group recommenders suggests close groups suit most pleasure, loose groups suit least misery, and average sits in between, and that people care most about avoiding misery and about fairness. The rule is a setting, chosen per group.
- Group sizes from 1 to N use the same code: with one person, the group score is just their personal score.
- Exclude places everyone in the group has been to; optionally keep places only some have been to and liked.
- Return the ranked list with the clusters and the per-person scores behind each recommendation.

### 8. Validation

- Hold out some of each person's rated places, run them through the pipeline as if unknown, and check whether places they rated highly come out near the top.
- Check that results hold across different combinations of people, and group sizes, not just one fixed group.
- Compare against crowd scores afterwards as a sanity check only.

## Possible planned steps

### Step 1: Standard input format

- Define one input format any person's list must follow: `person_id, restaurant_name, score, rank, price, cuisine, address, city`.
- Write a loader for a Beli export, and a template for lists transcribed from screenshots.
- Keep Toronto and Mississauga only (or a configurable city list).
- **Output:** `ratings_<person_id>.csv` per person.

### Step 2: Match restaurants into a shared pool

- Match each person's restaurants to a shared `restaurant_id` using name plus address (fuzzy name match, address check).
- Merge chain locations under one ID and average each person's scores across locations.
- Flag uncertain matches for manual review.
- **Output:** `restaurants.csv` (one row per unique place), `ratings_all.csv` (`person_id, restaurant_id, score`).

### Step 3: Compute percentiles

- Per person: `pct = 1 - (rank_of_score - 0.5) / N`, ties averaged.
- Record each person's list size; flag anyone with fewer than about 30 rated places as having a less reliable profile.

### Step 4: Build the reference restaurant set

- All restaurants from the pool, plus a broad sample of Toronto restaurants across cuisines, prices and neighbourhoods (target about 1,000 places).
- This set fixes the topics and clusters, so they do not depend on who is in the group.

### Step 5: Collect reviews

- **Yelp:** match each restaurant to its Yelp page (name plus address check), pull the newest 40 reviews.
- **Google Maps:** match to the Maps place page, pull the newest 40 reviews.
- Drop places with fewer than 10 reviews in total.
- **Output:** `reviews.csv` (`restaurant_id, source, review_id, date, text`).

### Step 6: Extract opinion units

- Remove duplicates, empty and non-English reviews.
- Run each review through an LLM with a fixed prompt and a few worked examples. Output per unit: `aspect, excerpt, sentiment (1 to 10)`. Drop general remarks with no aspect.
- Use a small, cheap LLM and batch requests; at about 1,000 restaurants and 80 reviews each this is around 80,000 reviews (about 450,000 units).
- Replace restaurant names and dish names that only appear at one place with a placeholder, so topics group by experience and not by restaurant.
- **Quality check:** hand-check 100 random reviews. Measure how many real aspects were found (recall), how many units are correct (precision), and whether sentiment is right. Fall back to sentence splitting if precision is under about 80%.
- **Output:** `units.csv` (`restaurant_id, source, review_id, unit_id, aspect, excerpt, sentiment`).

### Step 7: Choose an embedding model and embed

- Candidates:
  - `all-mpnet-base-v2` (768 dimensions): proven on restaurant review topics, runs on a laptop CPU. Starting point.
  - `Qwen3-Embedding-0.6B` (open, Apache-2.0, output size 32 to 1024, accepts a task instruction): stronger general model, needs a GPU at this corpus size.
  - `bge-m3`: open alternative.
  - A sentiment-aware model (such as SentiCSE): better at separating praise from complaints, slightly worse at grouping by topic. Only worth testing if the sentiment split from step 6 turns out noisy.
- **Pick** on a 5,000-unit sample: run steps 8 and 9 with each model and keep the one whose topics are most stable across seeds and easiest to name. Paid API models (OpenAI, Voyage) are not needed at this scale.
- Embed the text `aspect: excerpt` for every unit, normalize vectors to unit length, and cache them.
- **Output:** `unit_embeddings.npy`, row aligned with `units.csv`, plus the model name and version.

### Step 8: Fit and freeze the topic model

- Fit two topic models: one on positive units (sentiment 6 and up), one on negative units (5 and below).
- Pipeline for each: UMAP to about 5 dimensions, HDBSCAN to group units, c-TF-IDF for top words (BERTopic).
- Try minimum topic sizes of 20, 50 and 100 units, 5 seeds each. Pick the setting with the best coherence whose topics repeat across seeds (at least 80% top-word overlap).
- Merge topics with centroid cosine similarity above about 0.85.
- Name each topic from its top 10 words and 10 most representative units, map it to a standard aspect category (food, drinks, service, ambience, location, restaurant overall), and drop noise topics.
- Keep units HDBSCAN marks as noise unassigned; report the share (expected 15 to 30%).
- **Output:** `topic_model_pos_v1/`, `topic_model_neg_v1/`, `topics_v1.csv` (`topic_id, polarity, name, aspect_category, top_words`).

### Step 9: Build restaurant feature vectors

- Share of each restaurant's opinion units in each sentiment-split topic (rows sum to 1, noise excluded). "Great service" and "bad service" are separate columns.
- Baseline to compare in validation: the mean of all a restaurant's unit embeddings (one dense vector, no topics).
- Add cuisine family (one-hot) and price level (scaled); scale the three blocks to equal total variance so none dominates.
- **Output:** `features_v1.csv`, one row per restaurant.

### Step 10: Fit overlapping clusters

- **Primary method:** Gaussian mixture model on the feature vectors (PCA to about 80% of variance first). Each restaurant gets a membership probability for every cluster.
- **Number of clusters:** compare BIC across k = 5 to 20, check bootstrap stability (adjusted Rand index above about 0.7).
- **Alternative to compare:** fuzzy c-means with fuzziness m between 1.5 and 2.
- **Membership rule:** a restaurant belongs to every cluster where its membership is at least 0.2.
- Name each cluster from its highest-share topics, top cuisines and typical price.
- **Output:** `memberships_v1.csv`, `clusters_v1.csv`.

### Step 11: Build taste profiles

- For each person and cluster: membership-weighted average percentile, and effective number of rated places.
- Shrink clusters with few rated places toward the person's overall average.
- **Output:** `taste_<person_id>.csv` (cluster, weighted percentile, effective count), ranked.

### Step 12: Score and validate

- **Personal score:** sum over clusters of membership times that person's cluster percentile.
- **Validation:** 5-fold split of each person's rated places; fit the profile on 4 folds, score the held-out fold.
- **Metrics:** Spearman correlation between predicted and actual percentile, and top-third AUC.
- **Baselines:** random ranking and "predict the person's average"; the model only counts if it beats both.
- **Feature comparison:** run the same validation with sentiment-split topics, plain topic shares (no sentiment), and the mean-embedding baseline, to confirm the sentiment split earns its place.
- Repeat for every available person and group combinations of different sizes.

### Step 13: Group recommendations

- Take any list of `person_id`s as input (size 1 to N).
- Score every candidate restaurant for each person, then combine with the chosen group rule (average, least misery, trimmed average, average without misery, multiplicative or Borda).
- Exclude places everyone in the group has rated.
- Report how much the group agrees on each recommendation (spread of the personal scores).
- **Output:** `recs_<group_id>.csv` with the group score, each person's score, and the top clusters behind it.

### Step 14: Crowd check

- Compare top group recommendations against Beli global and friends' averages and Yelp and Google stars.
- Used only to spot obviously bad recommendations, not to change scores.

## v4 run (28 Oct 2026): what was built and what it found

### Data
- Lists: Wael 188 places, Z 184 (rank order, cleaned from screenshots). 202 unique Toronto-area places; 59 on both lists.
- Yelp match: 196 matched by name and neighbourhood; 6 had no real Yelp page and were dropped (Koh Rawi, Smash Daddy, August 8 Chinatown, Korean Grill House Spadina, Chestnut Dining Hall, Mexican Tortillas Burritos). Both IKEA entries matched the same listing and were merged.
- Reviews: 35 highest-rated + 5 closest-to-3-star per place, 5,874 reviews (5,818 after removing duplicates and non-English). Raw pulls are kept in `raw/` inside the data folder (combined file plus one file per restaurant), so nothing needs re-pulling.
- Sentences: 37,509 (restaurant names masked). Embedded with `all-mpnet-base-v2`; sentiment from `twitter-roberta-base-sentiment-latest` (positive 60%, neutral 29%, negative 11%). Embeddings and sentiment are in the data folder (`BELI_DATA`).

### Departures from the planned steps
- Yelp only (no Google Maps reviews yet) and sentence splitting instead of LLM opinion units (the plan's fallback).
- Minimum reviews per place lowered from 10 to 5, so 177 places keep features (134 of Wael's, 98 of Z's). Sparse aspects are shrunk toward neutral.
- Recommendation candidates are only the pool places; the ~1,000-place reference set (step 4) is not built yet.

### Topics
- 166 topics after dropping meta talk about ratings and reviews: 49 positive, 72 neutral, 59 negative, hand-tagged with 12 aspects (flavor, quality, portions, value, service, wait, ambience, location, logistics, menu, occasion, overall) or as dish identity.
- Settings chosen by stability across 3 seeds (seed agreement 0.52 to 0.69); 36% of sentences are unassigned, close to the expected 15 to 30% upper range.

### Validation (5-fold, repeated 5 times; Spearman / top-third AUC)
| Method | Wael (n=134) | Z (n=98) |
|---|---|---|
| Clusters, GMM | 0.16 / 0.58 | 0.11 / 0.56 |
| Clusters, fuzzy c-means | 0.11 / 0.55 | 0.03 / 0.50 |
| Nearest neighbours on review features | 0.22 / 0.63 | 0.27 / 0.67 |
| Cuisine average (baseline) | 0.04 / 0.47 | -0.13 / 0.43 |
| Ridge on aspect sentiment | 0.22 / 0.63 | 0.21 / 0.65 |
| **Ridge on aspect sentiment + talk rate** | **0.26 / 0.66** | **0.38 / 0.72** |
| Chance cutoff (95%) | 0.17 / 0.58 | 0.20 / 0.60 |

- Permutation test on the best model (200 shuffles): both p < 0.01, and both real scores beat the shuffled 99th percentile, which guards against having picked the best of seven methods.
- Clusters still do not predict held-out places, matching v3. They stay useful as a description of taste.

### What each person responds to (rank vs. net praise, Spearman)
- Both: food flavour is the strongest signal (Wael 0.32, Z 0.27), and it holds within cuisine.
- Wael: service 0.25, menu 0.21, overall 0.21, quality 0.19. The v3 portions link (0.32) did not hold on the larger list (0.02).
- Z: wait 0.29 (places people say are worth waiting for), menu 0.27, portions 0.21, overall within cuisine 0.31.
- Cuisine family alone predicts nothing for either person.

### Clusters (6, overlapping; 37% of places in 2+)
Sit-down with ambience and attentive service is the top cluster for both (Wael 65, Z 61 percentile). Complaint-heavy places are the bottom (46 / 41).

### Done after the first v4 run
- Topic model frozen (`pipeline/freeze.py`): new sentences go to the topic of their 15 nearest labelled sentences of the same polarity. 98% agreement with the original topics on held-out sentences.
- Reference set built (`pipeline/browser/reference.js`, `pipeline/refscore.py`): new restaurants from Yelp searches in the areas the two lists come from, 18 best + 2 average reviews each, scored with each person's model. See `results/new_places/`.
- LLM opinion units tested on 100 reviews (`docs/opinion_unit_test.md`): not adopted.

### Next steps
1. Add Google Maps reviews and more average or negative reviews per place; complaints are thin at 11%.
2. Add a third person's list and check whether the model holds up for them.
3. Log a few real dinners against the group picks to tune the misery cut-off.
