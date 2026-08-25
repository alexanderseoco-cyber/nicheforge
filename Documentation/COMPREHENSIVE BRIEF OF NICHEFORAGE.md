# COMPREHENSIVE BRIEF OF NICHEFORGE

## 1. Product identity

NicheForge is a Rank & Rent and Pay-Per-Call niche-validation engine. Its purpose is to convert a large pool of local-service opportunities into a smaller, evidence-backed shortlist of niches that may be worth building websites for.

The product follows the principle:

```text
Find → Validate → Rank
```

Its main process is:

```text
Niche or keyword
    ↓
City and geography resolution
    ↓
Population filter
    ↓
Search-volume filter
    ↓
Localized SERP acquisition
    ↓
Authority and competition evaluation
    ↓
Secondary SEO analysis
    ↓
Commercial and monetization review
    ↓
Final shortlist, history and ledger
```

NicheForge does not merely produce a score. It preserves the evidence, provider, timestamp, configuration, decision reason and historical lineage behind every result.

## 2. Problem solved

Manual Rank & Rent research repeatedly requires a user to:

1. Combine a service with a city.
2. Check population.
3. Check search demand.
4. Inspect localized Google results.
5. Examine ranking-domain authority.
6. Count weak competitors.
7. Review backlinks, referring domains, page authority and other signals.
8. Check whether the niche can be monetized.
9. Record the decision.
10. Repeat the process across many cities.

This causes duplicate work, inconsistent decisions, unnecessary provider calls, lost history and difficulty explaining why a candidate passed or failed.

NicheForge turns that activity into a configurable, staged and auditable validation funnel.

## 3. Core product concepts

### Project

A Project is a research workspace containing niches, cities, candidates, validation profiles, runs, evidence, decisions and history.

### City

A City contains the canonical city name, state, country, population, geographic identifiers, population vintage and provider-specific location mappings. NicheForge uses a local Census-based city registry so population and basic city resolution do not require a paid request for every candidate.

Duplicate city names are resolved using city, state and country together. City-name-only matching is not considered safe.

### Candidate

A Candidate is one exact niche/city opportunity, normally represented as:

```text
service term + city + state
```

Example:

```text
tree services + Albany, NY
```

### Run

A Run is one execution of the validation process. It stores the selected candidates, frozen profile settings, provider context, stage transitions, evidence references, errors, decisions and overrides.

### Validation Profile

A Validation Profile defines the rules for a run. Typical defaults are:

```text
Population: 20,000–120,000
Minimum search volume: 300
Weak-domain authority threshold: DA < 10
Required weak domains in Top 10: 4
Ideal weak domains: 5
SERP depth: 10
KD: optional, commonly < 15
```

Thresholds are configurable and snapshotted into the Run, so later profile changes do not rewrite historical decisions.

### Evidence

Evidence is a persisted result from a provider or local source. Important evidence types include:

- population evidence;
- search-volume and keyword-metric evidence;
- SERP snapshots and organic result rows;
- authority evidence;
- Ahrefs proxy-authority evidence;
- backlink and referring-domain evidence;
- keyword-difficulty evidence;
- currency and FX evidence.

Evidence normally stores its provider, values, raw or normalized payload, timestamp, freshness and lineage.

## 4. Technology stack

### Backend

The backend is a Python 3.12+ service using:

- FastAPI;
- Uvicorn;
- SQLAlchemy 2;
- Alembic;
- Pydantic 2;
- Pydantic Settings;
- HTTPX;
- `tldextract`;
- `python-multipart`;
- Google Ads SDK.

Important backend locations:

```text
backend/app/api/routes.py
backend/app/models/entities.py
backend/app/services/
backend/app/providers/
backend/alembic/versions/
```

### Frontend

The frontend uses:

- Next.js 15;
- React 19;
- TypeScript;
- the Next.js App Router;
- browser `fetch` calls to the FastAPI API;
- application CSS and component-level styles.

Important frontend locations:

```text
frontend/app/
frontend/app/rank-rent/validator/
frontend/app/research/search-volume/
frontend/app/components/
```

### Database

The project currently uses SQLite with Alembic-managed migrations. Core tables include:

```text
projects
cities
provider_location_identities
candidate_entities
project_candidates
runs
run_candidates
candidate_events
population_evidence
search_volume_evidence
keyword_metric_evidence
keyword_metric_batches
keyword_metric_validation_handoffs
serp_snapshots
serp_results
authority_evidence
proxy_authority_evidence
proxy_backlink_feature_evidence
provider_cache
provider_calls
```

### Testing

The backend uses pytest and pytest-asyncio with isolated databases, provider mocks, migration tests, failure-injection tests, cache tests and evidence-lineage tests. The frontend is checked with TypeScript and a production Next.js build.

## 5. Architectural layers

```text
Frontend UI
    ↓ HTTP/JSON
FastAPI routes
    ↓
Orchestration services
    ↓
Validation stages and business rules
    ↓
Provider interfaces
    ↓
Mock or real provider adapters
    ↓
Evidence, cache and telemetry persistence
    ↓
SQLite database
```

Provider-specific HTTP details remain inside adapters. The validation engine consumes normalized internal contracts rather than knowing vendor-specific request formats.

## 6. Provider architecture

Provider contracts are defined in `backend/app/providers/contracts.py` and selected through the provider factory.

### Search Volume

Search-volume providers return average monthly searches, monthly history, CPC, bids, competition, provider, target and timestamp. The main available path is Google Ads, with mock and imported-data paths also supported.

### SERP

The current live SERP provider is DataForSEO. It returns normalized organic results, rank, URL, title, domain, provider status, SERP features and raw response data.

### Authority

The authority contract supports exact URLs, root domains, DA, PA, spam score, referring domains and backlinks. The current authority provider is the deterministic mock provider. Moz has an adapter, but real activation is intentionally disabled until a Moz account and current API contract are available.

### Ahrefs

Ahrefs supplies domain-level DR evidence. Domains are normalized and deduplicated before requests are made.

### Backlinks

DataForSEO backlink processing also uses normalized root domains and stores backlink/referring-domain evidence as proxy backlink feature evidence.

### Population

Population primarily comes from versioned local Census data. This avoids a network request per candidate for basic geography and population filtering.

## 7. Complete validation process

### Step 1 — Intake

Users can enter niches or keywords manually, paste multiple lines, import text/CSV data, use Search Volume Research, or submit localized keyword handoffs.

### Step 2 — Normalization

NicheForge trims whitespace, normalizes Unicode, lowercases canonical values, collapses repeated spaces, identifies city/state terms, generates deterministic identities and removes duplicates while preserving original display text.

### Step 3 — Geography

The system either combines a service with eligible cities or resolves an already-localized keyword. City ambiguity is handled explicitly. Population evidence includes the raw population and data vintage.

### Step 4 — Population gate

Candidates outside the configured population range receive a population rejection state. They remain in the database and history rather than being deleted.

### Step 5 — Search-volume gate

Population survivors use stored or newly acquired search-volume evidence. If volume is below the configured threshold, the candidate is rejected at this stage. Changing the threshold can often recalculate from fresh stored evidence without a new provider call.

### Step 6 — Search Volume Research and handoff

The Search Volume page lets users research keywords, inspect demand and commercial metrics, select qualifying rows and send their canonical evidence IDs to the Validator. The Validator receives an evidence relationship, not just an untraceable copied number.

### Step 7 — Provider location resolution

Localized SERP requests require a verified DataForSEO location code:

```text
NicheForge City
    ↓
ProviderLocationIdentity
    ↓
DataForSEO location_code
    ↓
SERP request
```

If no verified mapping exists, the pipeline stops with a provider-location-unresolved state rather than guessing a location name or sending a malformed request.

### Step 8 — Localized SERP acquisition

The request includes the exact keyword, city, verified provider location code, country, language, device and requested depth. The response is stored as an immutable `SerpSnapshot` plus normalized `SerpResultRow` records.

### Step 9 — SERP classification

SERP results distinguish:

```text
VALID
PARTIAL_VALID
INSUFFICIENT
PROVIDER_ERROR
INVALID_TARGET
```

Provider errors are not misrepresented as genuine weak competition. Requested depth, observed usable depth and coverage ratio remain visible.

### Step 10 — SERP caching

SERP evidence is immutable while the cache pointer is mutable:

```text
ProviderCache pointer → SerpSnapshot evidence
```

When an old snapshot is invalid or stale, a successful new snapshot is created and the existing cache pointer is repointed. The old snapshot remains available for historical lineage. Failed acquisitions do not replace a safe cache pointer with failed evidence.

### Step 11 — URL and domain normalization

NicheForge preserves both exact URLs and normalized/root domains. This distinction is required because page-level metrics and domain-level metrics have different identities.

## 8. Authority and competition evaluation

### Current authority truth

All historical authority evidence currently uses:

```text
provider = mock
```

The mock values are deterministic development fixtures:

```text
DA = hash(root domain) modulo 50
PA = hash(exact URL) modulo 60
```

They are stable and useful for testing sorting, gates, caching and UI behavior, but they are not real Moz measurements and have no SEO meaning.

### DA primary gate

The primary authority gate counts organic domains below the configured DA threshold. With the common defaults:

```text
DA < 10
4 weak domains → PASS
5+ weak domains → IDEAL
0–3 weak domains → PRIMARY_REJECTED
```

A secondary score cannot convert a primary rejection into an automatic pass. Manual approvals preserve the original automatic result and the override reason.

### Adaptive authority evaluation

Adaptive evaluation can stop when the outcome is mathematically certain. Unchecked SERP positions remain explicitly unevaluated rather than being silently treated as having a value.

If mock authority affected the gate, the result is provisional and should be displayed as:

```text
PROVISIONAL — authority gate evaluated with mock evidence
```

## 9. Secondary analysis

Primary survivors may receive deeper analysis covering:

- PA distribution;
- Ahrefs DR;
- referring domains;
- backlinks;
- spam score;
- estimated traffic;
- indexed-page depth;
- local-business versus directory composition;
- Local Pack signals;
- title and meta quality;
- content and topical coverage;
- UX/mobile signals;
- trend stability;
- CPC and commercial intent;
- monetization suitability.

Secondary analysis ranks and explains candidates. It does not silently override failed primary gates.

## 10. Ahrefs and backlink workflow

The domain-level process is:

```text
SERP rows
    ↓
Root-domain normalization
    ↓
Deduplication
    ↓
Fresh-evidence lookup
    ↓
Reuse or provider acquisition
    ↓
Evidence persistence
```

Fresh Ahrefs and backlink evidence is reused according to policy, commonly for 30 days. Valid provider values of zero are preserved as real evidence rather than treated as missing.

## 11. Keyword Difficulty and monetization

Keyword Difficulty is a supporting metric evaluated after the primary authority process. It may classify candidates in priority mode or act as a configurable hard gate only after primary authority requirements pass.

Monetization is tracked separately from SEO eligibility. NicheForge can record Pay-Per-Call or Direct Rent routes, buyers, payouts, coverage, qualification rules, operating hours and traffic restrictions.

## 12. Final decision states

Common result states include:

```text
PASS
IDEAL
WATCHLIST
PRIMARY_REJECTED
ERROR_RETRYABLE
ERROR_TERMINAL
MANUALLY_APPROVED
NOT_PRODUCED
```

`NOT_PRODUCED` is used when a required upstream stage failed and an honest final decision cannot be generated.

## 13. Recalculation and history

Historical runs are preserved. When a threshold changes, NicheForge can create a new recalculation run using fresh stored evidence instead of repeating provider calls.

The system separates:

```text
Historical run      immutable record of what was decided
Recalculation run   new interpretation under new settings
Evidence            provider/local facts
Cache               currently reusable pointer
Telemetry           work and cost accounting
```

## 14. Cost-control architecture

NicheForge controls cost through a progressive funnel:

```text
Generated candidates
    ↓ population filter
Population survivors
    ↓ search-volume filter
Search-volume survivors
    ↓ SERP acquisition
SERP competitors
    ↓ domain deduplication and evidence reuse
Authority/backlink targets
    ↓ primary authority gate
Deep-analysis survivors
```

Other cost controls include batching, cache freshness, provider-location reuse, adaptive authority evaluation, parent-run reuse, retry limits, quotas and budget reservations.

## 15. Provider-cost telemetry

Provider telemetry measures provider economics before provider behavior is optimized. It records provider, operation, cache status, logical demand, unique targets, provider items, batches, HTTP requests, returned/failed items, retries, evidence reuse/creation, costs, currency, confidence and linkage to runs/candidates.

The system keeps these concepts separate:

```text
1,000 logical rows
        ↓
650 submitted provider items
        ↓
65 batches
        ↓
65 HTTP requests
```

Telemetry is observational. It must not change cache decisions, freshness, provider payloads, retries, gates, evidence lineage or candidate outcomes.

Telemetry writes are isolated and best-effort. If telemetry fails, provider execution, evidence persistence and validation must continue normally.

Known zero is distinct from unknown:

```text
0       known zero
NULL    unknown, not applicable or not measured
```

If a provider does not report monetary cost, NicheForge records unknown cost rather than assuming the operation was free.

## 16. Frontend functionality

### Overview

Provides navigation to research, validation, results, evidence, provider settings and account settings.

### Search Volume Research

Supports keyword entry/import, country selection, provider research, trend inspection, CPC and competition display, qualification thresholds, row selection, copying, CSV export and handoff to the Validator.

### Validator

Supports project and handoff recovery, city selection, mixed Local/General scope, validation profiles, run controls, stage progress, candidate expansion, SERP evidence, authority evidence, provider attribution, partial coverage and mock-authority warnings.

### Evidence and results

The UI exposes raw evidence and stage explanations instead of presenting only a final score. Missing downstream stages, provider errors, reused evidence and provisional authority are explicitly labeled.

## 17. Backend API areas

The FastAPI API provides endpoint groups for:

- application capabilities and country data;
- keyword metrics and Search Volume Research;
- Search Volume handoffs;
- projects and candidate generation;
- validation runs and execution;
- recalculation;
- candidate history and exports;
- provider-specific analysis;
- provider telemetry.

The frontend communicates with these routes using JSON requests and receives structured evidence/result projections.

## 18. End-to-end example

For:

```text
tree services + Albany, NY
```

the process is:

```text
1. Normalize the service and city identity.
2. Resolve Albany, NY from the local city registry.
3. Check population against the selected profile.
4. Reuse or acquire search-volume evidence.
5. Apply the search-volume gate.
6. Resolve the verified DataForSEO Albany location code.
7. Reuse or acquire the localized SERP.
8. Preserve the immutable snapshot and normalized organic rows.
9. Normalize exact URLs and root domains.
10. Reuse or acquire authority evidence.
11. Apply the DA primary gate.
12. If eligible, evaluate Ahrefs DR and backlink evidence.
13. Evaluate KD and secondary metrics where enabled.
14. Review monetization signals.
15. Produce PASS, IDEAL, WATCHLIST, rejection, retryable or not-produced state.
16. Persist evidence IDs, stage events, lineage and telemetry.
17. Project the result to the Validator UI and history.
```

If the provider returns only nine acceptable organic results and policy allows it, the result is `PARTIAL_VALID`. If the provider rejects the request, the result is a provider error rather than a fabricated weak-competition result.

## 19. Current reality and limitations

The following distinction must remain explicit:

### Real or provider-backed when configured

- Google Ads search-volume data;
- DataForSEO SERP data;
- verified DataForSEO location mappings;
- Ahrefs DR data;
- DataForSEO backlink data;
- local Census population data.

### Development-only

- mock DA;
- mock PA;
- mock provider responses;
- any evidence labeled `provider = mock`.

Moz is intentionally not active because a Moz account is not currently available. Therefore mock authority values must not be used as final SEO authority measurements or treated as production-grade niche decisions.

Other limitations include unknown cost when a provider does not report a charge, prospective rather than complete historical telemetry, optional secondary integrations and the difference between automated validation and manual browser acceptance.

## 20. Current project status

The repository has completed important reliability and measurement work, including:

- provider abstraction;
- local Census city registry;
- DataForSEO location-code resolution;
- immutable SERP snapshots;
- mutable SERP cache-pointer reconciliation;
- partial SERP coverage handling;
- truthful result presentation;
- mock authority provenance labeling;
- Google Ads telemetry;
- DataForSEO SERP telemetry;
- Ahrefs telemetry;
- DataForSEO backlink telemetry;
- telemetry failure isolation;
- evidence reuse accounting;
- provider-request accounting;
- migration validation;
- frontend production-build validation.

The completed provider-cost telemetry work was committed and pushed to GitHub as:

```text
55244ef feat: complete provider cost telemetry instrumentation
```

## 21. Operating rule

NicheForge should always prefer this interpretation:

```text
Evidence before conclusions.
Cheap gates before expensive requests.
Cache before acquisition.
Provider attribution before trust.
Immutable history before rewriting.
Truthful uncertainty before invented certainty.
```

In summary, NicheForge is a configurable, evidence-preserving Rank & Rent validation engine that transforms local-service ideas into auditable niche decisions through staged gates, provider adapters, persistent evidence, caching, reuse, batching, lineage and cost telemetry.

