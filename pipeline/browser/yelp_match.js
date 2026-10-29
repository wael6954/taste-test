// Step 2a: find each restaurant's Yelp listing.
// Set window.__Q = [[key, name, "Neighbourhood, City, ON"], ...] (built from the cleaned lists), then call __matchAll().
// Results go to localStorage.m4 as {key: {q, cands:[{slug,title,ctx}]}}; score them with ../lists/match.py.

window.__search = async ([k, name, loc]) => {
  const f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;left:0;top:0;width:1300px;height:1000px;opacity:0.01;pointer-events:none;z-index:-1;border:0';
  f.src = '/search?find_desc=' + encodeURIComponent(name.replace(/\(.*?\)/g, '')) + '&find_loc=' + encodeURIComponent(loc);
  document.body.appendChild(f);
  let out = null; const t0 = Date.now();
  while (Date.now() - t0 < 25000) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const d = f.contentDocument; if (!d) continue;
      if (/captcha|denied|blocked/i.test(d.title || '')) { out = { err: 'blocked:' + d.title }; break; }
      const seen = new Set(), c = [];
      for (const a of d.querySelectorAll('a[href^="/biz/"]')) {
        if (a.textContent.trim().length < 2 || a.getAttribute('href').includes('adredir')) continue;
        const s = a.getAttribute('href').split('?')[0].replace('/biz/', '');
        if (seen.has(s)) continue; seen.add(s);
        let card = a; for (let i = 0; i < 8 && card.parentElement; i++) { card = card.parentElement; if (card.textContent.length > 150) break; }
        c.push({ slug: s, title: a.textContent.trim().slice(0, 80), ctx: card.textContent.replace(/\s+/g, ' ').slice(0, 260) });
        if (c.length >= 6) break;
      }
      if (c.length) { out = { cands: c }; break; }
    } catch (e) {}
  }
  f.remove();
  return out || { err: 'timeout' };
};

window.__matchAll = async () => {
  const m4 = JSON.parse(localStorage.getItem('m4') || '{}');
  for (const q of window.__Q) {
    const [k] = q;
    if (m4[k] && !m4[k].err) continue;               // resume; retries earlier errors
    const r = await window.__search(q);
    if (r.err && r.err.startsWith('blocked')) { window.__mp = 'BLOCKED: clear the captcha in this tab, then run again'; return; }
    m4[k] = { q, ...r };
    localStorage.setItem('m4', JSON.stringify(m4));
    window.__mp = Object.keys(m4).length + '/' + window.__Q.length;
    await new Promise(r => setTimeout(r, 7000 + Math.random() * 6000));   // slow on purpose
  }
  window.__mp = 'DONE ' + Object.keys(m4).length + '/' + window.__Q.length;
};
