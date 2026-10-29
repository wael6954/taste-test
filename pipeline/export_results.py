"""Copy the shareable outputs from out/ to ../results, grouped by question (aggregates only: no review text, no embeddings)."""
import os, shutil, glob, pandas as pd
D = os.path.dirname(os.path.abspath(__file__)); OUT = f'{D}/out'; RES = os.path.join(os.path.dirname(D), 'results')
GROUPS = {
    'validation': ['validation_v4.json', 'permtest_ridge_talk.json', 'opinion_unit_test.json', 'topic_stability.json', 'k_selection.json', 'model_summary.json'],
    'taste': ['aspect_correlations_v4.json', 'taste_wael.csv', 'taste_zed.csv', 'ridge_coef_wael.csv', 'ridge_coef_zed.csv', 'clusters_v4.csv'],
    'recommendations': ['recs_summary.json'] + sorted(os.path.basename(f) for f in glob.glob(f'{OUT}/recs_*.csv')),
    'new_places': ['ref_summary.json', 'ref_predictions.csv'] + sorted(os.path.basename(f) for f in glob.glob(f'{OUT}/refrecs_*.csv')),
}
# clear old flat copies so the folder only holds the current layout
for f in glob.glob(f'{RES}/*.*'):
    if not f.endswith('README.md'): os.remove(f)
n = 0
for g, files in GROUPS.items():
    os.makedirs(f'{RES}/{g}', exist_ok=True)
    for f in files:
        if os.path.exists(f'{OUT}/{f}'): shutil.copy2(f'{OUT}/{f}', f'{RES}/{g}/{f}'); n += 1
# topics without the example sentences (those are quotes from Yelp reviews)
os.makedirs(f'{RES}/topics', exist_ok=True)
T = pd.read_csv(f'{OUT}/topics_tagged.csv'); T.drop(columns=['examples']).to_csv(f'{RES}/topics/topics_v4.csv', index=False); n += 1
print(n, 'files in', RES)
