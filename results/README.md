# results/

Shareable outputs from the latest pipeline run, written by `pipeline/export_results.py`. Aggregates and restaurant names only: no review text, no embeddings.

| Folder | What is in it |
|---|---|
| `validation/` | Held-out accuracy of every method (`validation_v4.json`), permutation test, topic stability across seeds, cluster-count selection, opinion-unit test |
| `taste/` | Aspect correlations per person, ridge weights, cluster profiles and each person's average per cluster |
| `topics/` | The 166 topics with aspect tag, polarity and size (example sentences removed) |
| `recommendations/` | Rankings over the rated pool, per person and for both under each group rule |
| `new_places/` | Predictions for restaurants neither person has rated, and the crowd check against Yelp stars |

Percentiles run from 0 to 1 within each person's own list. In `recommendations/`, a person's own rating replaces the prediction where they have been (`*_rated` columns say which).
