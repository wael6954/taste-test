// Step 3: sentences -> embeddings + 3-class sentiment, in the browser on WebGPU.
// Usage: localStorage.names = JSON.stringify({key: "Restaurant name", ...}); then __embedRun('pulls', 'v4')
// (or __embedRun('ref_pulls', 'ref') for the reference set). Resumable: finished chunks are remembered in localStorage.
// Output downloads: <prefix>_meta.json, <prefix>_emb_chunk_N.bin (float32 x 768), <prefix>_sent_chunk_N.bin (float32 x 3: neg, neu, pos).
// Rows inside chunks follow meta.order (sentences sorted by length, which makes batching ~3x faster).

const EMB_MODEL = 'Xenova/all-mpnet-base-v2';
const SENT_MODEL = 'Xenova/twitter-roberta-base-sentiment-latest';
const CHUNK = 4000;

window.__dl = (blob, name) => { const u = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 120000); };

window.__build = (storeKey, skip = ['ikeabistrodowntown']) => {
  const NAMES = JSON.parse(localStorage.getItem('names') || '{}'), pulls = JSON.parse(localStorage.getItem(storeKey));
  const seg = new Intl.Segmenter('en', { granularity: 'sentence' });
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const places = [], reviews = [], sents = [];
  for (const k of Object.keys(pulls).sort()) {                    // sorted keys -> the same build every time
    const v = pulls[k];
    if (skip.includes(k) || !v || !v.best) continue;
    const pi = places.length;
    places.push({ k, slug: v.slug, total: v.total, nbest: v.nbest, navg: v.navg, err: v.err || null });
    const nm = (NAMES[k] || '').replace(/\(.*?\)/g, '').split(/ - |\|/)[0].trim();
    const nameRx = nm.length >= 3 ? new RegExp('\\b' + esc(nm) + '(\'s)?\\b', 'gi') : null;
    const seen = new Set();
    for (const [r, src] of v.best.map(r => [r, 'best']).concat((v.avg || []).map(r => [r, 'avg']))) {
      const t = (r.text || '').trim(), sig = t.slice(0, 80);
      if (!t || seen.has(sig)) continue; seen.add(sig);                                   // drop duplicates
      if (r.lang && !String(r.lang).toLowerCase().startsWith('en')) continue;            // English only
      const ri = reviews.length;
      reviews.push({ p: pi, stars: r.stars, date: r.date, src, text: t });
      const clean = t.replace(/\s+/g, ' ').replace(/([a-z\)])([.!?])([A-Z])/g, '$1$2 $3');  // "salmon.The" -> "salmon. The"
      for (const { segment } of seg.segment(clean)) {
        let s = segment.trim();
        if (s.split(' ').length < 4) continue;
        if (nameRx) s = s.replace(nameRx, 'this place');           // topics should group experiences, not restaurants
        sents.push([pi, ri, s.slice(0, 600)]);
      }
    }
  }
  const order = [...Array(sents.length).keys()].sort((a, b) => sents[a][2].length - sents[b][2].length || a - b);
  return { places, reviews, sent: sents, order, chunk: CHUNK, model: EMB_MODEL, sentiment_model: SENT_MODEL };
};

window.__embedRun = async (storeKey = 'pulls', prefix = 'v4') => {
  const T = window.__T || await import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.0.2'); window.__T = T;
  const M = window.__build(storeKey); window.__M = M;
  const n = M.sent.length, nch = Math.ceil(n / CHUNK);
  if (!localStorage.getItem(prefix + '_meta_saved')) { window.__dl(new Blob([JSON.stringify(M)], { type: 'application/json' }), prefix + '_meta.json'); localStorage.setItem(prefix + '_meta_saved', String(n)); }
  for (const stage of ['emb', 'sent']) {
    let pipe = null;
    for (let c = 0; c < nch; c++) {
      const key = `${prefix}_${stage}_chunk_${c}`;
      if (localStorage.getItem(key)) continue;
      if (!pipe) pipe = stage === 'emb' ? await T.pipeline('feature-extraction', EMB_MODEL, { device: 'webgpu', dtype: 'fp32' })
                                       : await T.pipeline('text-classification', SENT_MODEL, { device: 'webgpu', dtype: 'fp32' });
      const ids = M.order.slice(c * CHUNK, (c + 1) * CHUNK), dim = stage === 'emb' ? 768 : 3, out = new Float32Array(ids.length * dim);
      for (let i = 0; i < ids.length;) {
        const L = M.sent[ids[i]][2].length, B = L > 400 ? 8 : L > 250 ? 16 : L > 150 ? 32 : 64;   // long sentences in small batches (big ones stalled WebGPU)
        const texts = ids.slice(i, i + B).map(j => M.sent[j][2]);
        if (stage === 'emb') out.set((await pipe(texts, { pooling: 'mean', normalize: true })).data, i * 768);
        else (await pipe(texts, { top_k: 3 })).forEach((labs, q) => { for (const { label, score } of labs) out[(i + q) * 3 + { negative: 0, neutral: 1, positive: 2 }[label.toLowerCase()]] = score; });
        i += texts.length; window.__ep = `${stage} chunk ${c + 1}/${nch}: ${i}/${ids.length}`;
      }
      window.__dl(new Blob([out.buffer]), `${key}.bin`); localStorage.setItem(key, String(out.length));
      await new Promise(r => setTimeout(r, 1500));
    }
    if (pipe && pipe.dispose) { try { await pipe.dispose(); } catch (e) {} }   // free GPU memory before the next model
  }
  window.__ep = 'ALL DONE ' + n;
};
