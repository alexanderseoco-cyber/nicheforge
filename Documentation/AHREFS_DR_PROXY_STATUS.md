# Ahrefs DR Proxy Status

## Contract verified

Official source: [Ahrefs Domain Rating free API](https://docs.ahrefs.com/en/api/reference/public/get-domain-rating-free).

- Method: `GET`
- Endpoint: `https://api.ahrefs.com/v3/public/domain-rating-free`
- Required query parameter: `target` containing a domain or URL
- Authentication: `Authorization: Bearer <token>`
- Primary metric: `domain_rating.domain_rating`
- Additional metadata: `domain_rating.license`, `domain_rating.warning`
- Cost: free and does not consume API units under the documented contract
- Attribution: `Domain Rating by Ahrefs` with an Ahrefs link wherever DR is displayed
- No API key is configured by this implementation pass
- No live Ahrefs request has been made
- Network execution requires both `AHREFS_PROXY_ENABLED=true` and `AHREFS_LIVE_APPROVED=true`
- Missing `AHREFS_API_KEY`, disabled proxy, or missing live approval blocks before transport

## Implemented boundary

Ahrefs DR is a separate `ahrefs/domain_rating/proxy_authority` evidence path. It is not Moz DA, cannot produce Moz PASS/IDEAL classifications, and does not alter the existing Moz provider or DA evaluator.

Proxy classifications are `PROXY_STRONG_CANDIDATE`, `PROXY_REVIEW`, `PROXY_REJECTED_HIGH_CONFIDENCE`, and `PROXY_DATA_INCOMPLETE`. Bootstrap calibration state is `UNCALIBRATED_HIGH_RECALL`; no DR-to-DA conversion is assumed.

Manual Moz observations and CSV imports use `manual_moz` provenance. When compatible Ahrefs evidence exists, paired observations are stored for future immutable calibration datasets.

## Safety status

- Existing CSV, population, SV, SERP, cache, Run/RunCandidate, ProviderCall, and Moz paths remain intact.
- Candidate count remains user-controlled.
- Ahrefs credentials are environment-only and redacted from request output.
- No live Ahrefs, Moz, or additional DataForSEO calls were made.
- Migration head: `a8ahrefsproxy`.
