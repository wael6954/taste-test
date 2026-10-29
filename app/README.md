# app/

`index.html` is the web app: a single self-contained page (data inlined, Plotly from a CDN). Open it in a browser, no server needed.

| Tab | What it shows |
|---|---|
| Picks | Ranked restaurants for Wael, Z, or both under a chosen group rule. Filters for area, price and name; "Been" mode compares the model's guess with the real rank. Each place shows the review features that push it up. |
| Taste | What drives each person's rankings, the six restaurant types, the topic table |
| 3D | Taste space, each person's prediction surface, and a map of review sentences |
| Pipeline | The review guide from `PIPELINE.md`, with a checkbox per stage |
| Checks | Validation against chance, permutation test, frozen-topic check, crowd check, opinion-unit test |

Rebuild with `python pipeline/build_app.py` after a pipeline run. `index_private.html` (git-ignored) also shows review sentences in the 3D hover; it is for local use only.
