const API_BASE = "http://localhost:8000/api/v1";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "NICHEFORGE_LOOKUP" || !Array.isArray(message.urls)) return;
  const urls = message.urls.filter(u => {
    try { const x = new URL(u); return x.protocol === "https:" || x.protocol === "http:"; }
    catch { return false; }
  }).slice(0, 20);

  // Endpoint is specified in blueprint; implementation lands with Phase 2 backend work.
  fetch(`${API_BASE}/overlay/metrics`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({urls})
  }).then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
    .then(data => sendResponse({ok:true, data}))
    .catch(error => sendResponse({ok:false, error:String(error)}));
  return true;
});
