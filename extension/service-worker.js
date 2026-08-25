const DEFAULT_API = "http://localhost:8000/api/v1";
let countryCatalog = [];
async function settings() { return new Promise(resolve => chrome.storage.local.get({apiBase: DEFAULT_API, accessToken: ""}, resolve)); }
async function api(path, init = {}) { const s = await settings(); const headers = {"Content-Type": "application/json", "Cache-Control": "no-cache", ...(init.headers || {})}; if (s.accessToken) headers.Authorization = `Bearer ${s.accessToken}`; const response = await fetch(`${String(s.apiBase).replace(/\/$/, "")}${path}`, {...init, cache: "no-store", headers}); const data = await response.json().catch(() => ({})); if (!response.ok) throw new Error(data.detail || `API request failed (${response.status})`); return data; }
async function googleAutocomplete(query) {
  const url =
    "https://www.google.com/complete/search?client=chrome&q=" +
    encodeURIComponent(String(query || "").trim());

  const response = await fetch(url, {
    method: "GET",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Google autocomplete failed (${response.status})`);
  }

  const data = await response.json();

  if (!Array.isArray(data) || !Array.isArray(data[1])) {
    return [];
  }

  return data[1]
    .map(item => Array.isArray(item) ? item[0] : item)
    .filter(item => typeof item === "string" && item.trim())
    .map(item => item.trim());
}
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "NS_GET_AUTOCOMPLETE") {
    const query = String(message.query || "").trim();

    if (!query) {
      sendResponse({ok: true, data: []});
      return true;
    }

    googleAutocomplete(query)
      .then(data => sendResponse({ok: true, data}))
      .catch(error => sendResponse({ok: false, error: error.message}));

    return true;
  }
  if (message?.type === "NS_RESEARCH_KEYWORDS") {
    const keywords = [...new Set(
      (Array.isArray(message.keywords) ? message.keywords : [])
        .map(keyword => String(keyword || "").trim().toLowerCase())
        .filter(Boolean)
    )].slice(0, 50);

    if (!keywords.length) {
      sendResponse({ok: false, error: "No keywords to research."});
      return true;
    }

    const countryCode = String(message.countryCode || "WORLD").trim().toUpperCase();
    const worldwide = ["WORLD", "WORLDWIDE", "GLOBAL"].includes(countryCode);
    const mapping = countryCatalog.find(row => row.country_code === countryCode);
    const target = worldwide
      ? {target_type: "WORLDWIDE"}
      : (mapping?.resource_name
        ? {geo_target_constants: [mapping.resource_name], country_code: countryCode}
        : {country_code: countryCode});

    api("/keyword-metrics/research", {
      method: "POST",
      body: JSON.stringify({
        keywords,
        provider: "google_ads",
        target: {
          country_code: worldwide ? "WORLD" : countryCode,
          language_code: "en",
          location_target: target
        }
      })
    })
      .then(data => sendResponse({ok: true, data, keywords}))
      .catch(error => sendResponse({ok: false, error: error.message}));

    return true;
  }

  if (message?.type === "NS_RESEARCH_KEYWORD") { const countryCode = String(message.countryCode || "WORLD").trim().toUpperCase(); const worldwide = ["WORLD", "WORLDWIDE", "GLOBAL"].includes(countryCode); const mapping = countryCatalog.find(row => row.country_code === countryCode); const target = worldwide ? {target_type: "WORLDWIDE"} : (mapping?.resource_name ? {geo_target_constants: [mapping.resource_name], country_code: countryCode} : {country_code: countryCode}); api("/keyword-metrics/research", {method: "POST", body: JSON.stringify({keywords: [String(message.keyword || "").trim()], provider: "google_ads", target: {country_code: worldwide ? "WORLD" : countryCode, language_code: "en", location_target: target}})}).then(data => sendResponse({ok: true, data})).catch(error => sendResponse({ok: false, error: error.message})); return true; }
  if (message?.type === "NS_LOOKUP_DR") { const urls = (Array.isArray(message.urls) ? message.urls : []).filter(u => { try { return ["http:", "https:"].includes(new URL(u).protocol); } catch { return false; } }).slice(0, 20); api("/overlay/metrics", {method: "POST", body: JSON.stringify({urls})}).then(data => sendResponse({ok: data.provider === "ahrefs", data})).catch(error => sendResponse({ok: false, error: error.message})); return true; }
  if (message?.type === "NS_GET_SETTINGS") { settings().then(data => sendResponse({ok: true, data})); return true; }
  if (message?.type === "NS_GET_COUNTRIES") { api("/geo/countries").then(data => { countryCatalog = Array.isArray(data) ? data : []; sendResponse({ok: true, data: countryCatalog}); }).catch(error => sendResponse({ok: false, error: error.message})); return true; }
  if (message?.type === "NS_SAVE_SETTINGS") { chrome.storage.local.set({apiBase: String(message.apiBase || DEFAULT_API).trim(), accessToken: String(message.accessToken || "").trim()}, () => sendResponse({ok: true})); return true; }
});
