# Integration of Search Volume and Trend

## Governing architecture

NicheForge will implement a provider-neutral, standalone **Keyword Metrics Engine**. It will research and cache search volume, trends, CPC, competition, and bid metrics without applying a universal threshold. Stored evidence may be explicitly handed to any validation profile.

```text
Keyword input/import → Keyword Metrics Engine → immutable evidence/cache
                                      ├→ research workspace/API
                                      └→ explicit validation handoff
```

Google Ads is an optional provider implementation, not a production dependency. DataForSEO, CSV imports, and future providers remain replaceable.

## Execution order

### Phase 0 — Contract and architecture freeze

- Record this plan as the governing artifact.
- Verify Google Ads official historical-metrics contract before implementing its provider.
- Confirm batching, geo/language targeting, quotas, OAuth, access requirements, close-variant behavior, response fields, and caching rules.
- Make no live provider request.

### Phase 1 — Models and migrations

Add canonical models for keyword queries, immutable metric evidence, batches, and provider-result mapping. Store submitted keyword and provider-returned canonical/close-variant keyword separately.

Evidence includes SV, monthly history, CPC, competition, bids, trend data, provider, provenance, targeting, timestamps, freshness, and sanitized raw payload. Refresh creates a new evidence row and updates a current/cache pointer; it never overwrites historical evidence.

Preserve compatibility with existing `SearchVolumeEvidence` and imported SV records.

### Phase 2 — Provider abstraction

Create a provider-neutral interface supporting single/bulk queries, targeting, response mapping, partial results, errors, and batch accounting. Implement mocks, CSV/import compatibility, existing DataForSEO compatibility, and later the Google Ads provider.

### Phase 3 — Configuration and safety guards

Add independent provider settings. Live transport requires enablement, explicit approval, and credentials. Defaults remain disabled. Never display, log, hash, or persist credentials.

Provider cost semantics must distinguish `0`, `null/unknown`, and positive paid cost. Free requests still create truthful ProviderCalls.

### Phase 4 — Cache identity

Cache keys include normalized submitted keyword, location, targeting mode, country, language, provider, and metric version. City-targeted and city-embedded queries remain distinct. Freshness, stale reuse, refresh, deduplication, and restart behavior are explicit.

### Phase 5 — Bulk batch engine

Support arbitrary user-controlled input sizes. Normalize, deduplicate, preview cache hits, chunk only for provider limits, map results exactly, preserve unmapped results, persist append-only evidence, link one truthful ProviderCall per actual request, and resume safely.

Provider limits are internal chunking constraints, never product-level limits.

### Phase 6 — Research APIs

Build backend contracts before UI:

- preview;
- single/bulk research;
- CSV import;
- listing/filtering;
- evidence detail;
- refresh;
- export;
- explicit send-to-validation handoff.

Research mode has no mandatory SV or population threshold.

### Phase 7 — Validation handoff

Explicitly selected research evidence may become candidate input to a validation Run. The handoff preserves targeting, provenance, and evidence lineage, avoids fresh requests when compatible evidence exists, and supports arbitrary selections.

### Phase 8 — Validation profile refactor

SV policy belongs to profiles, not evidence. For example, Local SEO Rank & Rent may default to population `20,000–120,000` and SV `≥260`; other profiles may use different thresholds or disable the gate. Threshold changes reuse evidence without refetching.

### Phase 9 — UI workspace

After APIs stabilize, add one/bulk input, keyword×city generation, targeting selection, cache preview, result tables, SV/CPC/trend/competition filters, freshness/provider labels, exports, and explicit validation handoff.

### Phase 10 — Google Ads provider implementation

Implement OAuth/account configuration, historical metrics requests, geo/language resources, limits, provider-keyword identity mapping, sanitized raw responses, and cost/status accounting. A live smoke test requires separate authorization and is not part of implementation.

### Phase 11 — Compatibility and recalculation

Verify CSV SV imports, DataForSEO evidence, existing Runs, SERP/Moz/Ahrefs/backlink isolation, exports, restart, recalculation, immutable evidence, and multiple profiles consuming identical evidence without duplication or refetch.

### Phase 12 — Acceptance

Test single/bulk research, arbitrary counts, normalization, close variants, exact identity mapping, cache/stale refresh, partial responses, cost semantics, safety guards, append-only evidence, restart, handoff, profile thresholds, migration from zero, upgrade, and no unnecessary provider calls.

Validation sequence:

```text
targeted tests → migration tests → full suite → compilation → git diff --check → status
```

No automatic commit or live Google Ads/DataForSEO/Moz/Ahrefs/SV request during implementation.

## Definition of done

The engine accepts any number of keywords, supports targeting, persists immutable provider-specific evidence and provider-returned identities, reuses cache, distinguishes zero/unknown/paid costs, exposes APIs before UI, exports results, has no universal SV threshold, supports explicit validation handoff, applies profile-specific policies, preserves historical Runs, and lets multiple profiles consume the same evidence without duplication or refetch.
