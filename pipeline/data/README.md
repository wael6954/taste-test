# data/ (not committed)

Raw inputs can live here or anywhere else: set the environment variable `BELI_DATA` to that folder and every script reads from it instead (for example `BELI_DATA=~/Documents/beli-taste-data bash pipeline/run_all.sh`). Keeping them outside the repo is safer, since nothing in them should ever be committed.

Everything here is either personal or Yelp content, so it stays out of git. The pipeline expects:

```
data/
  lists/
    lists_raw.json        # OCR'd Beli lists: {person: [{rank, name, score, loc, cu}]}
    lists_final.json      # cleaned lists (output of lists/clean.py)
    places.json           # deduplicated Toronto-area places with each person's ranks
    final_slugs.json      # restaurant key -> Yelp slug (after lists/match.py + manual fixes)
    m4_full.json          # raw Yelp search results used for matching (also gives Yelp stars for the crowd check)
  v4_meta.json            # sentences, reviews, places (from browser/embed.js)
  v4_emb_chunk_*.bin      # float32 x 768
  v4_sent_chunk_*.bin     # float32 x 3 (neg, neu, pos)
  ref_meta.json, ref_*_chunk_*.bin, ref_cand.json   # reference set, same format
  opinion_units/          # hand-extracted opinion units for the 100-review test
```

To use your own lists, export or transcribe them into `lists_final.json` / `places.json` format; nothing in the pipeline is tied to two people.
