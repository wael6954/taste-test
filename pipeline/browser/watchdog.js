// Optional: pause a long reference pull while the tab is hidden and restart it when the tab is visible again.
// Hidden tabs render Yelp pages so slowly that every page times out and gets marked as an error.
window.__autoResume = setInterval(() => {
  const running = window.__rp && !/^(STOPPED|ALL DONE|BLOCKED)/.test(window.__rp);
  if (document.visibilityState !== 'visible') { if (running) window.__stopRef = true; return; }
  if (window.__rp === 'STOPPED') { window.__stopRef = false; window.__runRef(); }
}, 15000);
