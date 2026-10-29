// Step 7: build the reference set of new restaurants (places neither person has rated).
// Needs yelp_reviews.js loaded first (for __fr, __page, __pullOne).
// window.__plan = [[location, pages], ...]; v4 used the neighbourhoods the two lists come from, weighted by how often they appear.
// Then: await __discover(); await __runRef();  Results: localStorage.ref_cand, localStorage.ref_pulls.

window.__searchPage = async (loc, start) => {
  const f = window.__fr;
  f.src = '/search?find_desc=Restaurants&find_loc=' + encodeURIComponent(loc) + (start ? '&start=' + start : '');
  const t0 = Date.now(); await new Promise(r => setTimeout(r, 2500));
  while (Date.now() - t0 < 30000) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const d = f.contentDocument; if (!d || !d.location.href.includes('/search')) continue;
      if (/captcha|unusual activity/i.test(d.title)) return { err: 'blocked' };
      const out = [], seen = new Set();
      for (const a of d.querySelectorAll('a[href^="/biz/"]')) {
        const s = a.getAttribute('href').split('?')[0].replace('/biz/', ''), t = a.textContent.trim();
        if (!t || t.length < 2 || seen.has(s) || /^\d+$/.test(t) || /^more$/i.test(t)) continue;
        let card = a; for (let i = 0; i < 12 && card.parentElement; i++) { card = card.parentElement; if (/\(\d[\d,]* reviews?\)/.test(card.textContent) && card.textContent.length > 120) break; }
        seen.add(s); out.push({ slug: s, title: t.replace(/^\d+\.\s*/, ''), ctx: card.textContent.replace(/\s+/g, ' ').slice(0, 400) });
      }
      if (out.length >= 5 && d.readyState === 'complete') return { res: out };
    } catch (e) {}
  }
  return { err: 'timeout' };
};

window.__discover = async () => {
  const pool = new Set(Object.values(JSON.parse(localStorage.getItem('pulls') || '{}')).map(v => v.slug));   // skip places already rated
  const cand = JSON.parse(localStorage.getItem('ref_cand') || '{}'), done = JSON.parse(localStorage.getItem('ref_pages_done') || '[]');
  for (const [loc, np] of window.__plan) for (let p = 0; p < np; p++) {
    const id = loc + '|' + p; if (done.includes(id)) continue;
    window.__dprog = id;
    let r = await window.__searchPage(loc, p * 10);
    if (r.err === 'blocked') { window.__dprog = 'BLOCKED at ' + id; return; }
    if (r.err) { await new Promise(x => setTimeout(x, 20000)); r = await window.__searchPage(loc, p * 10); if (r.err) continue; }
    for (const c of r.res) {
      // ranked results only ("1. Name4.5 (65 reviews)Neighbourhood$$..."); skips ads and "Order" buttons
      if (c.title === 'Order' || !/^\d+\.\s/.test(c.ctx) || pool.has(c.slug) || cand[c.slug]) continue;
      const m = c.ctx.match(/^\d+\.\s(.+?)([\d.]+)\s\((\d[\d,]*) reviews?\)(.*?)(\${1,4})?(Open|Closed|"|$)/);
      if (!m) continue;
      cand[c.slug] = { slug: c.slug, title: c.title, stars: +m[2], nrev: +m[3].replace(/,/g, ''), hood: (m[4] || '').trim(), price: m[5] ? m[5].length : null, q: loc };
    }
    done.push(id); localStorage.setItem('ref_pages_done', JSON.stringify(done)); localStorage.setItem('ref_cand', JSON.stringify(cand));
    await new Promise(x => setTimeout(x, 8000 + Math.random() * 6000));
  }
  window.__dprog = 'DONE ' + Object.keys(cand).length;
};

window.__runRef = async (minReviews = 10) => {
  const cand = JSON.parse(localStorage.getItem('ref_cand') || '{}'), res = JSON.parse(localStorage.getItem('ref_pulls') || '{}');
  for (const slug of Object.values(cand).filter(c => c.nrev >= minReviews).map(c => c.slug)) {
    if (res[slug] && !res[slug].err) continue;
    if (window.__stopRef) { window.__rp = 'STOPPED'; return; }
    window.__rp = slug;
    let r; try { r = await window.__pullOne(slug, 18, 2); } catch (e) { r = { slug, err: 'exception:' + e.message, nbest: 0 }; }
    if (r.err === 'best:blocked') { window.__rp = 'BLOCKED at ' + slug; return; }
    res[slug] = r; localStorage.setItem('ref_pulls', JSON.stringify(res));
    await new Promise(x => setTimeout(x, 1000 + Math.random() * 1500));
  }
  window.__rp = 'ALL DONE ' + Object.keys(res).length;
};
