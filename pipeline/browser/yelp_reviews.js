// Step 2b: pull reviews for each matched listing.
// Set window.__pullList = [[key, slug], ...] (from final_slugs.json), then call __runPulls().
// Per restaurant: NBEST highest-rated reviews (sort_by=rating_desc) + NAVG reviews closest to 3 stars from the default sort.
// v4 used NBEST=35, NAVG=5; the reference set used 18 + 2 (see reference.js).

const NBEST = 35, NAVG = 5;

// One persistent iframe kept on-screen (but invisible) so Yelp's lazy-loaded reviews actually render.
window.__fr = window.__fr || (() => {
  const f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;left:0;top:0;width:1300px;height:1000px;opacity:0.01;pointer-events:none;z-index:-1;border:0';
  document.body.appendChild(f); return f;
})();

// Review cards differ between page 1 and later pages, so start from each review body (span[lang])
// and walk up to the closest element that also holds a star rating.
window.__extract = (d) => {
  const out = [];
  for (const sp of d.querySelectorAll('span[lang]')) {
    let el = sp, star = null;
    for (let i = 0; i < 10 && el; i++) { star = el.querySelector('[aria-label*="star rating"]'); if (star) break; el = el.parentElement; }
    if (!star) continue;
    const m = el.textContent.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4}\b/);
    out.push({ stars: +star.getAttribute('aria-label').match(/[\d.]+/)[0], date: m ? m[0] : null, lang: sp.getAttribute('lang'), text: sp.textContent });
  }
  return out;
};

// Load one review page and wait until the number of reviews is stable for two checks.
window.__page = async (f, url, maxw = 40000) => {
  f.src = url; const t0 = Date.now(); const slug = url.split('?')[0].split('/biz/')[1];
  await new Promise(r => setTimeout(r, 1500)); let last = -1, stable = 0;
  while (Date.now() - t0 < maxw) {
    await new Promise(r => setTimeout(r, 800));
    try {
      const d = f.contentDocument; if (!d || !d.location.href.includes(slug)) continue;
      // check visible text only: Yelp's translation bundle contains the word CAPTCHA on every page
      const head = d.title + ' ' + (d.body && d.body.innerText ? d.body.innerText.slice(0, 600) : '');
      if (/captcha|unusual activity|access denied|are you a robot/i.test(head)) return { err: 'blocked' };
      try { f.contentWindow.scrollTo(0, d.body.scrollHeight * (0.3 + 0.1 * (stable % 4))); } catch (e) {}
      const revs = window.__extract(d);
      if (revs.length && revs.length === last) stable++; else stable = 0; last = revs.length;
      if ((revs.length && stable >= 2) || (!revs.length && Date.now() - t0 > 25000 && d.readyState === 'complete')) {
        const tm = d.body.textContent.match(/\(([\d,]+) reviews?\)/);
        return { revs, total: tm ? +tm[1].replace(/,/g, '') : null };
      }
    } catch (e) {}
  }
  return { err: 'timeout' };
};

window.__pullOne = async (slug, nbest = NBEST, navg = NAVG) => {
  const f = window.__fr, base = 'https://www.yelp.ca/biz/' + slug, best = []; let total = null, err = null;
  for (let s = 0; s < Math.ceil(nbest / 10) * 10 && best.length < nbest; s += 10) {
    if (total != null && s >= total) break;
    let r = await __page(f, base + '?sort_by=rating_desc' + (s ? '&start=' + s : ''));
    if (!r.err && !r.revs.length && s === 0) { await new Promise(x => setTimeout(x, 15000)); r = await __page(f, base + '?sort_by=rating_desc'); }
    if (r.err) { err = 'best:' + r.err; break; }
    if (r.total) total = r.total;
    for (const rv of r.revs) if (best.length < nbest) best.push(rv);
    if (!r.revs.length) break;
    await new Promise(x => setTimeout(x, 900 + Math.random() * 700));
  }
  const seen = new Set(best.map(r => (r.text || '').slice(0, 50))), pool = [];
  for (let s = 0; s < 20 && pool.length < 3 * navg && !err && (total == null || total > best.length); s += 10) {
    if (total != null && s >= total) break;
    const r = await __page(f, base + (s ? '?start=' + s : ''));
    if (r.err) { err = 'avg:' + r.err; break; }
    for (const rv of r.revs) if (!seen.has((rv.text || '').slice(0, 50))) pool.push(rv);
    if (!r.revs.length) break;
    await new Promise(x => setTimeout(x, 900 + Math.random() * 700));
  }
  pool.sort((a, b) => Math.abs(a.stars - 3) - Math.abs(b.stars - 3));
  const avg = pool.slice(0, navg);
  if (!err && best.length === 0 && (total || 0) > 0) err = 'empty';   // rendered but nothing extracted: retry later
  return { slug, total, err, nbest: best.length, navg: avg.length, best, avg };
};

window.__runPulls = async (storeKey = 'pulls') => {
  const res = JSON.parse(localStorage.getItem(storeKey) || '{}');
  const good = v => v && !v.err && v.nbest > 0 && (v.nbest >= 25 || (v.total != null && v.nbest >= v.total - 5));
  for (const [key, slug] of window.__pullList) {
    if (good(res[key])) continue;
    if (window.__stopPull) { window.__pp = 'STOPPED'; return; }
    window.__pp = key;
    let r; try { r = await window.__pullOne(slug); } catch (e) { r = { slug, err: 'exception:' + e.message, nbest: 0 }; }
    if (r.err === 'best:blocked') { window.__pp = 'BLOCKED: clear the captcha, then run again'; return; }
    res[key] = r; localStorage.setItem(storeKey, JSON.stringify(res));
    window.__pdone = Object.keys(res).length;
    await new Promise(x => setTimeout(x, 1000 + Math.random() * 1500));
  }
  window.__pp = 'ALL DONE ' + Object.keys(res).length;
};

// Save everything as one JSON download.
window.__exportPulls = (storeKey = 'pulls', name = 'yelp_raw_pulls.json') => {
  const blob = new Blob([localStorage.getItem(storeKey)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
};
