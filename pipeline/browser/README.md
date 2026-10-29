# Browser stage

These scripts run in a browser tab on `https://www.yelp.ca` (any page on that origin; `https://www.yelp.ca/robots.txt` is the lightest). They are pasted into the developer console or injected by an automation tool. Everything is kept in the tab's `localStorage`, so a reload or crash loses at most the current item.

Run them in this order:

| File | What it does | Writes |
|---|---|---|
| `yelp_match.js` | Searches Yelp for each restaurant (name + neighbourhood) and records up to 6 candidate listings | `localStorage.m4`, scored by `../lists/match.py` |
| `yelp_reviews.js` | For each matched listing: the 35 highest-rated reviews (`sort_by=rating_desc`, 4 pages) and the 5 reviews closest to 3 stars from the default sort | `localStorage.pulls` |
| `embed.js` | Splits reviews into sentences, masks the restaurant's own name, embeds with `Xenova/all-mpnet-base-v2` and scores sentiment with `Xenova/twitter-roberta-base-sentiment-latest` on WebGPU, in blocks of 4,000 sentences | downloads `<prefix>_meta.json`, `<prefix>_emb_chunk_N.bin`, `<prefix>_sent_chunk_N.bin` |
| `reference.js` | Finds new restaurants through Yelp search pages for chosen neighbourhoods and pulls 18 best + 2 average reviews each | `localStorage.ref_cand`, `localStorage.ref_pulls` |

`watchdog.js` (optional) pauses the reference pull while the tab is hidden and restarts it when it is visible again.

`collect_downloads.py` renames the browser's downloads into the chunk files the Python stage expects.

## Things that went wrong and are handled here

- **Background tabs are throttled.** A puller in a tab that is not in front, or in a hidden browser pane, slows to a crawl and its pages never finish rendering. Keep the tab in front and visible; `watchdog.js` pauses and resumes the reference pull automatically. Failed places are retried on the next run.
- **Yelp's first page and later pages use different HTML.** Reviews are found by walking up from each `span[lang]` review body to the nearest star rating, which works on both.
- **"Blocked" false positives.** Yelp's translation bundle contains the text "Complete the CAPTCHA to continue." Only the page title and visible text are checked.
- **Zero-review pages are errors.** A page that renders but yields no reviews is marked `empty` so it gets retried, instead of being saved as a valid empty result.
- **Rate.** About one page every 4 to 8 seconds with random gaps. Faster search loops hit Yelp's captcha after about 80 searches.

Respect Yelp's terms of service. The pulled review text is for personal analysis and is not redistributed in this repo.
