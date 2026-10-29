# Decisions and changes

What was decided at each point, and why. Newest first.

## v4.1 (28 Oct 2026, later the same day)

- **New places.** The plan's reference set was built from Yelp search pages in the neighbourhoods the two lists come from, instead of a city-wide list of about 1,000 places. Places with at least 10 Yelp reviews were pulled (18 best + 2 closest to 3 stars each), so the set reflects where the two of you actually go.
- **Frozen topics.** New restaurants never refit the topic model. Their sentences are assigned by nearest neighbours to the existing topics, so the features of rated places never move.
- **Talk-rate calibration.** Nearest-neighbour assignment leaves slightly more sentences unassigned than the original clustering did, which would lower every talk rate. Talk rates for new places are rescaled by the ratio of assigned shares.
- **Opinion units not adopted.** An LLM finds about 2.5 times more opinions, but adding the extra food opinions made prediction worse. Sentences stay.
- **Search-card parsing fix.** The first parse of some Yelp search cards took the previous card's stars and review count (Gusto 101 had Public Gardens' numbers). `pipeline/fix_cand.py` re-parses them; where the card text belongs to another listing entirely (4 places, e.g. Mildred's Temple Kitchen), stars and area are cleared rather than kept wrong. Stars are a check only, so predictions were unaffected.
- **Full reference set.** 326 new places, 6,234 reviews, 39,678 sentences. The pull ran in two sessions; the browser was restarted in between and resumed from the saved progress.
- **Web app.** One page (`app/index.html`) with picks, taste drivers, 3D views, the pipeline review guide and the checks. Data is inlined so it works from disk.
- **Repo layout.** Results grouped by question; `PIPELINE.md` and the app's Pipeline tab come from one source (`pipeline/stages.py`).

## v4 (28 Oct 2026)

- **Full lists.** Both people's complete Beli lists instead of samples: 151 and 110 Toronto places, 59 shared.
- **35 best + 5 average reviews.** Best reviews say what a place does well; a few middling ones catch complaints. Yelp stars are never an input.
- **3-class sentiment.** Binary sentiment (v1 to v3) forced neutral statements into praise or complaint. RoBERTa 3-class keeps them apart.
- **Talk rate as a feature.** How much reviewers mention an aspect, not only how positively. This is what made Z's list predictable.
- **Minimum 5 reviews per place** (plan said 10), keeping 177 places. Sparse aspects are shrunk toward neutral.
- **Ridge per person as the predictor, clusters as the summary.** Clusters describe taste well but barely beat chance on held-out places.
- **Group default: average without misery.** Drop any place where either person lands below the 35th percentile, then average.

## v1 to v3

Earlier versions on a smaller first dataset (91 and 75 places), removed from the repo but kept in git history (commit 0a89aa6). v1 used binary sentiment and GMM clusters, v2 split dish from experience topics, v3 added cuisine-relative aspects. The main lessons carried forward: cuisine alone does not predict either list, and clusters do not predict on their own.
