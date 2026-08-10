function organicLinks() {
  const seen = new Set();
  const rows = [];
  for (const a of document.querySelectorAll('a')) {
    const h3 = a.querySelector('h3');
    if (!h3 || !a.href || seen.has(a.href)) continue;
    try {
      const u = new URL(a.href);
      if (!/^https?:$/.test(u.protocol)) continue;
      seen.add(a.href);
      rows.push({a, url:a.href});
    } catch {}
  }
  return rows.slice(0, 10);
}

function render(rows, metricsByUrl) {
  for (const row of rows) {
    if (row.a.parentElement?.querySelector(':scope > .nicheforge-metrics')) continue;
    const m = metricsByUrl[row.url];
    if (!m) continue;
    const el = document.createElement('div');
    el.className = 'nicheforge-metrics';
    el.style.cssText = 'font-size:12px;margin-top:2px;color:#356;';
    el.textContent = `DA ${m.da ?? 'N/A'} (Moz) | PA ${m.pa ?? 'N/A'} (Moz) | RD ${m.linking_root_domains ?? 'N/A'} | Spam ${m.spam_score ?? 'N/A'}`;
    row.a.parentElement?.appendChild(el);
  }
}

async function refresh() {
  const rows = organicLinks();
  if (!rows.length) return;
  chrome.runtime.sendMessage({type:'NICHEFORGE_LOOKUP', urls:rows.map(x=>x.url)}, response => {
    if (!response?.ok) return;
    render(rows, response.data?.by_url || {});
  });
}

refresh();
new MutationObserver(() => { clearTimeout(window.__nfTimer); window.__nfTimer=setTimeout(refresh,400); })
  .observe(document.documentElement, {subtree:true, childList:true});
