const $ = id => document.getElementById(id);
const countryNames = new Intl.DisplayNames([navigator.language || "en"], {type: "region"});
chrome.runtime.sendMessage({type: "NS_GET_COUNTRIES"}, response => { if (!response?.ok || !Array.isArray(response.data)) return; const select = $("country"); const current = select.value; const rows = response.data.filter(row => /^[A-Z]{2}$/.test(row.country_code)).sort((a, b) => String(a.country_code).localeCompare(String(b.country_code))); select.innerHTML = '<option value="WORLD">Worldwide (default)</option>' + rows.map(row => `<option value="${row.country_code}">${countryNames.of(row.country_code) || row.country_code}</option>`).join(""); select.value = rows.some(row => row.country_code === current) ? current : "WORLD"; });
chrome.runtime.sendMessage({type: "NS_GET_SETTINGS"}, response => { if (response?.ok) { $("apiBase").value = response.data.apiBase || ""; $("accessToken").value = response.data.accessToken || ""; }});
$("save").addEventListener("click", () => { chrome.runtime.sendMessage({type: "NS_SAVE_SETTINGS", apiBase: $("apiBase").value, accessToken: $("accessToken").value}, () => { $("result").textContent = "Settings saved."; }); });
$("research").addEventListener("click", () => { const keyword = $("keyword").value.trim(); if (!keyword) { $("result").textContent = "Enter a keyword first."; return; } $("result").textContent = "Researching with Google Ads…"; chrome.runtime.sendMessage({type: "NS_RESEARCH_KEYWORD", keyword, countryCode: $("country").value}, response => { if (!response?.ok) { $("result").textContent = response?.error || "Research failed."; return; } const item = response.data?.results?.[0]; if (!item) { $("result").textContent = "No mapped Google Ads result."; return; } $("result").textContent = `Volume: ${item.avg_monthly_searches?.toLocaleString?.() ?? "—"}\nCPC: ${item.usd_cpc == null ? "—" : `$${Number(item.usd_cpc).toFixed(2)}`}\nCompetition: ${item.competition_index ?? item.competition ?? "—"}\nProvider: ${item.provider}`; }); });

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[character])
  );
}

function trendDirection(item) {
  const values = (Array.isArray(item.monthly_history) ? item.monthly_history : [])
    .map(row => Number(row.searches || 0));

  if (values.length < 2) return "—";
  return values.at(-1) > values[0] ? "↑" : values.at(-1) < values[0] ? "↓" : "→";
}

function renderKeywordFinder(data, keywords) {
  const results = new Map(
    (data?.results || []).map(item => [
      String(item.submitted_keyword || "").toLowerCase(),
      item
    ])
  );

  const rows = keywords.map(keyword => {
    const item = results.get(keyword.toLowerCase()) || {submitted_keyword: keyword};
    const volume = item.avg_monthly_searches?.toLocaleString?.() ?? "—";
    const cpc = item.usd_cpc == null ? "—" : `$${Number(item.usd_cpc).toFixed(2)}`;
    const competition = item.competition_index ?? item.competition ?? "—";

    return `<tr><td>${escapeHtml(item.submitted_keyword || keyword)}</td><td>${volume}</td><td>${cpc}</td><td>${escapeHtml(competition)}</td><td>${trendDirection(item)}</td></tr>`;
  });

  $("finderResult").innerHTML =
    `<table class="keyword-metrics"><thead><tr><th>Keyword</th><th>Search volume</th><th>Avg CPC</th><th>Competition</th><th>Trend</th></tr></thead><tbody>${rows.join("")}</tbody></table>`;
}

$("findKeywords").addEventListener("click", () => {
  const seed = $("finderKeyword").value.trim();

  if (!seed) {
    $("finderResult").textContent = "Enter a seed keyword first.";
    return;
  }

  $("finderResult").textContent = "Getting autocomplete suggestions…";

  chrome.runtime.sendMessage(
    {type: "NS_GET_AUTOCOMPLETE", query: seed},
    autocompleteResponse => {
      if (!autocompleteResponse?.ok) {
        $("finderResult").textContent =
          autocompleteResponse?.error || "Autocomplete request failed.";
        return;
      }

      const keywords = [...new Set(
        [seed, ...(autocompleteResponse.data || [])]
          .map(keyword => String(keyword || "").trim().toLowerCase())
          .filter(Boolean)
      )].slice(0, 50);

      $("finderResult").textContent = "Getting Google Ads metrics…";

      chrome.runtime.sendMessage(
        {type: "NS_RESEARCH_KEYWORDS", keywords, countryCode: $("country").value},
        metricsResponse => {
          if (!metricsResponse?.ok) {
            $("finderResult").textContent =
              metricsResponse?.error || "Google Ads research failed.";
            return;
          }

          renderKeywordFinder(metricsResponse.data, metricsResponse.keywords || keywords);
        }
      );
    }
  );
});
