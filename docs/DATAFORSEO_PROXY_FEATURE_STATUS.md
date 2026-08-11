# DataForSEO Proxy Feature Enrichment Status

## Verified official contract

Sources: [Bulk Pages Summary Live](https://docs.dataforseo.com/v3/backlinks-bulk_pages_summary-live/), [Backlink Summary Database fields](https://docs.dataforseo.com/v3/databases-backlink_summary/), and [Backlinks overview](https://docs.dataforseo.com/v3/backlinks-overview/).

- Endpoint: `POST https://api.dataforseo.com/v3/backlinks/bulk_pages_summary/live`
- Request body: generic POST array containing one task with `targets`
- Target limit: up to 1,000 pages, domains, or subdomains per request
- Domain restriction: URLs in one request cannot belong to more than 100 different domains
- Domain target format: domain/subdomain without `https://` and `www.`
- Response fields implemented: `rank`, `backlinks`, `referring_domains`, `referring_main_domains`, `referring_ips`, `referring_subnets`, nofollow domain counts, and `backlinks_spam_score`
- Rank scale: provider supports `one_hundred` and `one_thousand`; the implementation preserves the provider value and does not reinterpret it
- Retrieval method: official Backlinks documentation states the Backlinks API supports Live retrieval
- Pricing: the official endpoint documents request-based charging and directs users to current pricing; no unverified fixed price is hard-coded
- Rate limits: endpoint-specific account limits remain account/documentation dependent and are not invented in code

## Architecture

DataForSEO backlink features are separate from both Ahrefs DR and Moz DA. They are stored as `dataforseo` / `proxy_backlink_features` evidence and can populate multiple feature fields from one provider response and one ProviderCall.

No live backlink request has been made. The adapter requires both `DATAFORSEO_BACKLINK_PROXY_ENABLED=true` and `DATAFORSEO_BACKLINK_LIVE_APPROVED=true` before transport.

The calibration target remains `P(Moz DA < 10)`. No DR-to-DA formula or provider substitution is implemented.
# Mapper and raw-response observability

The Bulk Pages Summary response is mapped from `tasks[0].result[0].items[]`. The
target identity is `item.url` (normalized to the root domain); `item.target` is
not part of the documented live response shape. Core metrics are copied only
when present, and missing values remain null.

Each persisted feature evidence row records `mapping_status` and
`mapping_error`. Successful live responses also retain a sanitized provider
response envelope and the mapped item, excluding transport headers and
credentials. Mapping failures are not treated as valid reusable evidence.

The first five-domain live experiment predated raw-response persistence. Its
ProviderCall and actual cost (`$0.02418`) are preserved, while its five feature
rows are marked `unrecoverable_raw_missing`; no second provider request was
made.
