# Lists

The Beli lists came in as phone screenshots, transcribed with `tesseract` and parsed into `lists_raw.json` (rank, name, score, location, price + cuisine). Inputs live in `../data/lists/` (git-ignored).

- `clean.py`: fixes names OCR garbled, drops entries on request, repairs scores that break the ranked order, flags Toronto-area (GTA) places. Writes `lists_final.json` and one CSV per person.
- `match.py`: scores Yelp search candidates (`m4_full.json` from `../browser/yelp_match.js`) by name similarity and neighbourhood. Confident matches need similarity ≥ 0.8; the rest are reviewed by hand, with fixes recorded in `final_slugs.json`.

In v4: 202 unique Toronto-area places, 196 matched (6 had no real Yelp listing), 2 IKEA entries pointing to one listing were merged.

If Beli adds an export, replace the screenshot step with a loader that writes the same `lists_final.json` / `places.json` format.
