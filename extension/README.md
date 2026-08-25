# NicheForge Scout

NicheForge Scout (`NS`) is the focused browser companion for NicheForge.

It adds two signals to Google Search:

- Google Ads keyword metrics for the current query;
- Ahrefs Domain Rating (`DR`) beside organic-result domains.

Existing Google or competitor metrics are not replaced. Ahrefs DR is never
displayed as Moz DA.

## Local installation

1. Start the NicheForge backend on `http://localhost:8000`.
2. Ensure Google Ads is configured and approved in the backend environment.
3. Ensure Ahrefs DR is configured with `AHREFS_PROXY_ENABLED=true` and
   `AHREFS_LIVE_APPROVED=true` when live requests are intended.
4. Open Chrome and visit `chrome://extensions`.
5. Enable **Developer mode**.
6. Choose **Load unpacked** and select this `extension` folder.
7. Open the extension popup and save the API URL and access token if the
   backend is not running in single-user mode.
8. Search Google. The NS bar shows Google Ads volume/CPC/competition, while
   green `DR` badges appear beside organic domains when Ahrefs returns a
   domain-rating result.

## Safety and provenance

- Keyword requests use the Google Ads provider explicitly.
- DR requests use the `/overlay/metrics` route, which is Ahrefs-only.
- The overlay refuses to label mock authority or Moz authority as Ahrefs DR.
- A missing or unavailable DR value appears as `DR —` or remains absent.
- The content script suppresses duplicate requests for the same query and
  result set while Google mutates the page.
- API credentials are stored in Chrome local extension storage. Use a
  dedicated account/token and do not share the extension profile.
