# LLM opinion units vs. sentence splitting

The plan called for extracting **opinion units** (aspect, excerpt, sentiment 1 to 10) with an LLM, with sentence splitting as the fallback. v4 used the fallback. This test checks what that costs.

## Setup

- 100 random reviews from the v4 pull (seed 42).
- Opinion units extracted by hand with an LLM-style prompt: one unit per aspect mention, general remarks kept as `overall`. That gave 465 units.
- Compared per review and aspect: does the sentence pipeline (topic tag + 3-class sentiment) find the same aspect with the same polarity?

## Results

| Measure | Value |
|---|---|
| Units per review (LLM) | 4.65 |
| Sentences per review | 5.95 |
| Sentences unassigned or dish-only | 56% |
| LLM review-aspects also found by the pipeline (recall) | 39% |
| Pipeline review-aspects the LLM agrees with (precision) | 73% |
| Same polarity when both found it | 78% |
| Negative opinions found | 39% |
| Reviews with more units than sentences (two opinions in one sentence) | 31 of 100 |

By aspect, service and wait are caught best and flavour worst (21 of 72): most flavour opinions sit in dish topics ("the tacos were amazing"), which carry no aspect.

## Follow-up

Counting dish-topic sentences as flavour raised flavour recall to 0.79 at 0.80 precision. But prediction got worse: Wael's held-out Spearman fell from 0.26 to 0.21 and Z's from 0.38 to 0.36. Dish sentences in top-rated reviews are almost all positive, so they dilute the flavour signal. v4 keeps flavour as flavour topics only.

## Takeaway

LLM extraction would capture roughly 2.5 times more opinions, and it would split sentences that hold two opinions. Whether that improves prediction is not shown. The signal that does predict comes from what reviewers choose to talk about and complain about, and that is already partly visible at sentence level. Worth trying on a larger, less positive sample, such as Google reviews or more average-rated Yelp reviews.

Code: `pipeline/ou_compare.py`. The extracted units contain review excerpts, so they stay in the git-ignored `pipeline/data/opinion_units/`.
