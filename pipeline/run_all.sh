#!/usr/bin/env bash
# Python stage of the pipeline. Run from anywhere after the browser stage has produced data/ (see browser/README.md).
# Each line is one stage of PIPELINE.md; outputs go to out/ (git-ignored), shareable copies to ../results, the app to ../app.
set -euo pipefail
cd "$(dirname "$0")"
# Raw inputs live in data/ by default; set BELI_DATA to keep them elsewhere (e.g. BELI_DATA=~/Documents/beli-taste-data).
DATA="${BELI_DATA:-data}"
python ratings.py            # 1. percentiles, restaurant table (cuisine family, price)
python topics.py v4          # 5. sentiment-split topic models (UMAP + HDBSCAN), c-TF-IDF names
python tag_topics.py         #    first-pass aspect tags (keyword scoring) -> out/topics_autotag.csv
python tags_manual.py        #    reviewed aspect tags and names -> out/topics_tagged.csv
python model.py              # 6-7. features, clusters, taste profiles, 5x5-fold validation, predictions
python permtest.py           # 7. permutation test for the best model
python recs.py               # 8. per-person and group recommendations from the rated pool
python freeze.py             # 9. freeze the topic model for new restaurants
if [ -f "$DATA/ref_cand.json" ]; then python fix_cand.py "$DATA/ref_cand.json"; fi
if [ -f "$DATA/ref_meta.json" ]; then python refscore.py ref; fi   # 9. score new restaurants, if pulled
if [ -d "$DATA/opinion_units" ]; then python ou_compare.py; fi    # opinion-unit vs sentence-split test
python build_viz_data.py && python viz3d_data.py               # 10. app data (3D layout, taste summaries)
python app_data.py && python app_data.py --private
python stages.py ../PIPELINE.md                                #     review guide (also feeds the app's Pipeline tab)
python build_app.py --private
python export_results.py
python make_figures.py
