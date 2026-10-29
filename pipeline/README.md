# pipeline/

Two stages. The **browser stage** (`browser/`) talks to Yelp and runs the neural models on the GPU; it writes into `data/`. The **Python stage** (this folder) does everything else; `run_all.sh` runs it in order in about 2 minutes once the UMAP cache exists (10 minutes without).

| Order | Script | Stage in PIPELINE.md | Writes to `out/` |
|---|---|---|---|
| 1 | `lists/clean.py`, `ratings.py` | 1. Lists | `ratings_all.csv`, `restaurants.csv` (this folder) |
| 2 | `lists/match.py` | 2. Match | `data/lists/final_slugs.json` |
| 3 | `topics.py`, `tag_topics.py`, `tags_manual.py` | 5. Topics | `sentences.csv`, `topics_tagged.csv`, `emb_kept.npy` |
| 4 | `model.py` | 6-7. Features, models | `features_v4.csv`, `validation_v4.json`, `pred_*.csv`, `clusters_v4.csv` |
| 5 | `permtest.py` | 7. Models | `permtest_ridge_talk.json` |
| 6 | `recs.py` | 8. Group recs | `recs_*.csv` |
| 7 | `freeze.py` | 9. New places | `topic_model_v4/` |
| 8 | `fix_cand.py`, `refscore.py ref` | 9. New places | `ref_predictions.csv`, `refrecs_*.csv` |
| 9 | `ou_compare.py` | 4. Opinion-unit test | `opinion_unit_test.json` |
| 10 | `build_viz_data.py`, `viz3d_data.py`, `app_data.py` | 10. Pages | `viz_data.json`, `viz3d_data.json`, `app_data.json` |
| 11 | `stages.py ../PIPELINE.md`, `build_app.py` | 10. App | `../PIPELINE.md`, `../app/` |
| 12 | `export_results.py` | | `../results/` |

Template: `app_tpl.html` (data is injected at build time).

`data/`, `out/` and `topic_model_v4/` are git-ignored: they hold personal ratings, Yelp review text and embeddings. `data/README.md` lists what goes in `data/`.
