# NicheForge — Project Blueprint

**Version:** 1.0.0  
**Role:** Permanent engineering source of truth  
**Product:** NicheForge — Rank & Rent Niche Intelligence Engine  
**Tagline:** Find. Validate. Rank.

---

# 0. How to Use This Blueprint

This document is normative. IDE agents, developers and future maintainers must treat it as the first reference for architecture, naming, workflow behavior, data semantics and implementation decisions.

If implementation differs from this document, one of two things must happen:

1. implementation is corrected to match the blueprint; or
2. an Architecture Decision Record (ADR) is added under `docs/adr/`, explicitly explaining why the blueprint is being changed, and this document is updated in the same change.

Chat messages are not durable architecture. The repository documents are.

The blueprint intentionally distinguishes:

- **primary gates** — determine automatic eligibility;
- **secondary signals** — improve ranking, prioritization and confidence but do not silently override a failed primary gate;
- **commercial filters** — establish whether a ranking opportunity can be monetized;
- **provider data** — evidence, not business rules;
- **user overrides** — explicit, auditable decisions.

---

# 1. Product Problem

Manual Rank & Rent niche validation becomes prohibitively repetitive when one niche must be tested across hundreds or thousands of cities. A human workflow typically repeats:

- generate `service + city`;
- verify population;
- check search volume;
- open a localized SERP;
- inspect the organic Top 10;
- look up Moz Domain Authority for every ranking domain;
- count how many sites are below a DA threshold;
- if the candidate survives, inspect PA, referring domains, backlinks, Spam Score, indexed footprint, UX/on-page weakness, local reviews, trend and monetization;
- record results manually;
- repeat.

This creates several failure modes:

- duplicate work;
- inconsistent thresholds;
- human transcription errors;
- spending expensive API calls on candidates already doomed by cheap filters;
- losing a ledger of previously tested combinations;
- over-weighting attractive secondary metrics despite failure of the main competition criterion;
- inability to revisit rejected candidates when the user changes thresholds.

NicheForge solves this by turning the workflow into a configurable, evidence-preserving funnel.

---

# 2. Product Definition

NicheForge is a local SEO opportunity validation platform specialized for Rank & Rent / Pay-Per-Call research.

It accepts one or more of the following:

- broad categories (`pest control`);
- micro-niches (`rodent control`);
- nano-niches (`rat removal`);
- service names (`dryer vent repair`);
- already-localized keywords (`rodent control salina ks`);
- CSV/XLSX exports containing SV/KD/traffic data;
- city lists;
- provider result files.

It then progressively enriches each candidate with geography, demand, SERP and authority data while applying user-selected gates.

The final product is not merely a score. It is a fully auditable evidence row explaining:

- what was checked;
- by which provider;
- when;
- what values were returned;
- which configured rule passed or failed;
- why the final automatic state was assigned;
- whether a human overrode it.

---

# 3. Domain Language

## 3.1 Broad Category

High-level service family. Examples: `pest control`, `cleaning`, `roofing`.

## 3.2 Micro-Niche

Focused commercial service family suitable for a specialized local site. Examples: `rodent control`, `dryer vent cleaning`, `chimney repair`.

## 3.3 Nano-Niche / Sub-Niche

More specific service or intent inside a micro-niche. Examples: `rat removal`, `dryer vent repair`, `chimney cap repair`.

## 3.4 Candidate

One exact keyword/location opportunity processed by the engine. Normally:

`service_term + city + state`

Example:

`rodent control salina ks`

## 3.5 Project

A user-defined research workspace containing niches, configuration, candidates, runs, evidence and decisions.

## 3.6 Run

An immutable snapshot of configuration and processing for a set of candidates.

## 3.7 Primary Gate

A rule whose failure prevents automatic PASS.

Initial primary gates:

- population;
- search volume;
- low-DA distribution in organic Top 10.

## 3.8 Secondary Signal

A ranking/competition signal that influences the secondary score or warning set but normally does not override a failed primary gate.

## 3.9 Ledger

The persistent history of every niche/city combination and its latest and historical outcomes.

---

# 4. Canonical Workflow

Business priority is `Population -> SV -> DA -> deeper SERP analysis -> KD -> Current Result / History`. Technically, because DA is computed from discovered organic competitors, execution is `Population -> SV -> SERP acquisition -> DA primary gate -> deeper SERP analysis -> KD -> Result / History`. SERP acquisition is the Top-N competitor retrieval required for DA; it must remain conceptually distinct from later deeper SERP analysis. KD is a later supporting/prioritization signal and must not outrank or override the DA primary criterion. A KD HARD_GATE may reject only after DA has passed.

## Stage 0 — Intake

User creates a project and supplies any number of niches or localized keywords.

The UI must support:

- paste multiline text;
- CSV upload;
- XLSX upload;
- manual table entry;
- API submission;
- future discovery-provider import.

There is no product-level keyword count ceiling. The implementation may chunk work into safe provider/job sizes.

## Stage 1 — Normalize

For each input:

- trim whitespace;
- lowercase canonical keyword while retaining original display string;
- normalize Unicode;
- collapse repeated spaces;
- detect whether a city/state is already included;
- resolve niche hierarchy if user supplied it;
- calculate deterministic candidate identity;
- deduplicate inside the project;
- check ledger/cache before new paid calls.

Candidate identity should be based on normalized:

`project-independent service term + city geo id + language + country`

The project association is separate so the same cached provider data can be reused across projects.

## Stage 2 — Geography

Two modes:

### Generation mode

User supplied niche only. Engine joins the niche against the selected city universe.

### Import mode

User supplied already-localized keywords. Engine resolves city/state and population.

The population dataset is local, versioned data. It should not require an API call per candidate.

Default profile:

- min population: 20,000
- max population: 120,000
- exclude Alaska/Hawaii when the selected research profile says so

Both min and max are configurable.

The raw population value and dataset vintage must be stored.

Rejected candidates are not deleted. They receive `POPULATION_REJECTED` and a reason code.

## Stage 3 — Search Volume Gate

Only geography survivors proceed unless the user disables population gating.

The user configures:

- volume provider;
- minimum volume;
- match semantics/provider mode;
- language;
- location granularity;
- whether combined sibling/nano volume is enabled;
- whether provider disagreement is a warning or hard gate.

Default minimum: 300.

The threshold is not hardcoded. User may set 250, 400, 500 or any valid nonnegative number.

Important behavior:

- the system stores raw provider SV regardless of threshold;
- changing threshold recalculates eligibility from stored data where still fresh;
- changing threshold does not automatically trigger a fresh provider call;
- if a lower threshold causes previously rejected rows to re-enter, processing resumes from the next missing stage.

### Combined sibling volume

Combined volume is a separate explicit mode. It must not silently combine unrelated terms.

A `niche_family_id` groups sibling services. The UI must show both:

- individual local SV;
- aggregate family SV.

Primary-gate policy can be selected:

- `INDIVIDUAL_ONLY`
- `FAMILY_AGGREGATE_ALLOWED`
- `MANUAL_REVIEW`

## Stage 4 — SERP Retrieval

Only SV survivors request localized SERPs.

Required parameters:

- exact candidate keyword;
- target city/location;
- country;
- language;
- device profile (desktop default; mobile future option);
- result depth (10 default).

The system stores the raw SERP response and normalized organic result rows.

The primary gate considers organic results only unless a future profile explicitly changes that rule.

The system should also parse, when available:

- Local Pack presence;
- ads presence;
- PAA presence;
- organic rank;
- title;
- URL;
- display domain.

## Stage 5 — URL/Domain Normalization

For each organic result:

- preserve exact URL;
- canonicalize scheme/host casing;
- strip tracking query parameters for identity when safe;
- derive registered/root domain using a Public Suffix List aware parser;
- preserve subdomain;
- classify result type when possible: local business, directory/aggregator, government, social, marketplace, other authority.

Moz DA is domain-level evidence; PA is page-level evidence. The data model must never confuse them.

## Stage 6 — Moz Authority Enrichment

For the Top 10 organic URLs/domains:

- look in metric cache;
- fetch only missing/stale rows from the configured authorized Moz provider;
- store provider raw response;
- store DA;
- store PA when available;
- store Spam Score when available;
- store linking root domains and link counts when available.

Do not substitute an internally invented authority score for Moz DA while labeling it Moz.

If Moz API access is unavailable, the system may support:

- official Moz export import;
- manual metric paste;
- mock provider for development.

The candidate remains `AUTHORITY_PENDING` until sufficient authoritative data exists.

## Stage 7 — Primary DA Gate

Configuration:

- `da_threshold` default `10`
- comparison operator default `<`
- `required_low_da_count` default `5`
- `organic_depth` default `10`

Example:

For DA values:

`4, 6, 35, 8, 72, 3, 9, 18, 7, 40`

count where DA < 10 = 6.

With required count 5 -> PASS.

The user may change either value.

Examples:

- DA <10, require 5
- DA <10, require 4
- DA <15, require 5

Changing the gate recalculates from cached raw metrics; it does not refetch Moz unless data is stale.

If the low-DA count fails, automatic state becomes `PRIMARY_REJECTED`.

No secondary score can convert `PRIMARY_REJECTED` into automatic `PASS`.

A user may manually approve the row, but it must display `MANUALLY_APPROVED` and preserve the automatic failure.

## Stage 8 — Secondary Analysis

Only primary survivors receive expensive secondary processing by default.

Secondary dimensions:

1. Page Authority distribution
2. Referring domains
3. Total backlinks
4. Spam Score
5. Estimated competitor organic traffic
6. Indexed-page/site-depth estimate
7. Local business vs. directory composition
8. EMD/PMD/branded pattern
9. Local Pack review strength
10. SEO title quality
11. Meta-description presence/quality
12. Content depth
13. topical coverage
14. internal-linking quality where detectable
15. page speed / obvious technical UX
16. mobile UX
17. business age/history when available
18. trend stability
19. CPC/commercial signal
20. emergency/urgent intent
21. nationwide offer availability
22. payout suitability
23. geographic scalability
24. topical sibling expansion potential

Every secondary metric has:

- raw value;
- normalized score 0..100 when applicable;
- configured weight;
- direction (`lower_is_better`, `higher_is_better`, categorical mapping);
- provider/source;
- timestamp;
- completeness state.

## Stage 9 — Secondary Score

The score is a prioritization mechanism, not the main gate.

Recommended formula:

`weighted_score = sum(metric_score * active_weight) / sum(active_weight_of_available_metrics)`

The denominator uses only available metrics so missing data does not automatically become a zero.

The UI must separately show:

- secondary score;
- data-completeness percentage;
- missing evidence.

Default weights must be stored in a named profile and editable.

## Stage 10 — Monetization Validation

Commercial status is tracked separately from SEO eligibility.

Fields:

- route: `PAY_PER_CALL`, `DIRECT_RENT`, `UNKNOWN`
- network/buyer
- offer name
- active state
- coverage type: nationwide / state / ZIP / city
- eligible geographies
- payout
- qualification duration
- appointment requirement
- traffic-source restrictions
- operating hours
- duplicate-call rule
- call-recording requirements
- last verified timestamp

Nationwide status means monetization can accept calls from broad U.S. geography; it does not replace local SV or local SERP validation.

## Stage 11 — Final Decision

Automatic statuses:

### PASS

All enabled primary gates pass; any hard commercial gates pass; secondary data meets optional minimum score if configured.

### WATCHLIST

Primary SEO gates pass but secondary/commercial evidence is incomplete or warning-heavy.

### PRIMARY_REJECTED

At least one primary gate failed.

### MANUAL OVERRIDE

Explicit user decision with required reason.

---

# 5. Threshold and Profile System

Thresholds must be configuration records, never magic constants spread through code.

A `ValidationProfile` contains:

- population min/max
- included/excluded states
- SV minimum
- SV provider
- DA threshold
- DA comparison operator
- required low-DA count
- organic result depth
- KD optional threshold
- trend policy
- local review warning threshold
- monetization hard/soft rules
- secondary weights
- cache freshness policies

Built-in profile examples:

### Instructor Strict

- population 20k–100k
- local SV 400 preferred profile value
- DA <10
- require 5
- KD <15 optional
- non-seasonal preferred
- nationwide preferred

### Expanded Research

- population 20k–120k
- local SV 300
- DA <10
- require 5
- KD optional
- family aggregation supported

### User Custom

All editable.

Profiles are versioned. Each run stores a frozen snapshot rather than a foreign key only, so later edits do not rewrite historical decisions.

---

# 6. Provider Architecture

Provider code lives behind internal interfaces.

## 6.1 SearchVolumeProvider

Contract:

```python
class SearchVolumeProvider(Protocol):
    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]: ...
```

Result fields:

- keyword
- location key
- average monthly searches
- monthly history if available
- CPC
- paid competition
- provider
- raw payload
- fetched_at

Implementations planned:

- `DataForSEOKeywordProvider`
- `GoogleAdsKeywordProvider`
- `KeywordsEverywhereCsvProvider`
- `AhrefsCsvProvider`
- `MockKeywordProvider`

### Google Ads implementation facts

Google Ads Keyword Planning supports keyword ideas and historical metrics through `KeywordPlanIdeaService`. It requires Google Ads authentication/developer access and is separately rate limited. Provider code must throttle and batch accordingly.

### DataForSEO implementation facts

DataForSEO exposes keyword/search-volume endpoints and historical metrics. It also supplies CPC and paid competition. Credentials are server-side only.

## 6.2 SerpProvider

Contract:

```python
class SerpProvider(Protocol):
    async def fetch(self, requests: list[SerpRequest]) -> list[SerpResult]: ...
```

Result must normalize:

- organic results
- rank
- URL
- title
- domain
- optional SERP features
- raw response

Implementation:

- `DataForSEOSerpProvider`
- future other providers
- `MockSerpProvider`

DataForSEO regular Google Organic SERP returns localized results; top 10 is the default behavior in its task API. Use Advanced only when richer SERP features are required.

## 6.3 AuthorityProvider

Contract:

```python
class AuthorityProvider(Protocol):
    async def fetch(self, targets: list[AuthorityTarget]) -> list[AuthorityResult]: ...
```

Result:

- exact URL
- root domain
- DA
- PA
- Spam Score if supported
- linking root domains if supported
- backlinks if supported
- provider
- raw payload
- fetched_at

Implementations:

- `MozAuthorizedProvider`
- `MozCsvProvider`
- `MockAuthorityProvider`

Important: because vendor API contracts can change, endpoint paths and field mappings belong only inside the provider adapter. The domain engine consumes normalized fields and must not know Moz HTTP details.

## 6.4 PopulationProvider

Preferred implementation is a local repository over versioned Census data.

Interface supports:

- list eligible cities by min/max population;
- lookup city/state;
- return canonical geographic ID;
- dataset vintage.

## 6.5 ReviewsProvider

Future DataForSEO Business Data / Maps provider or equivalent.

## 6.6 MonetizationProvider

Future API/import adapters for offer data. The system must support manual records because many networks may not expose stable public APIs.

---

# 7. Cost-Control Architecture

Cost control is a first-class feature.

## 7.1 Progressive funnel

Do not fetch downstream data before upstream survival.

Example:

10,000 generated candidates
-> 7,500 population survivors
-> 1,000 SV survivors
-> 1,000 SERP calls
-> unique-domain authority enrichment with cache
-> 110 DA survivors
-> 110 deep analyses

## 7.2 Domain metric deduplication

A Top-10 domain can appear in hundreds of SERPs. DA should be cached by normalized root domain and reused until stale.

PA is cached by canonical URL.

## 7.3 Provider batch sizes

Each adapter defines:

- max batch size;
- rate limit;
- concurrency limit;
- retry policy;
- backoff;
- idempotency strategy.

The orchestration layer chunks work accordingly.

## 7.4 Freshness defaults

Suggested initial defaults, user-adjustable:

- population: until new dataset vintage
- keyword SV: 30 days
- SERP: 3 days
- DA/PA/link metrics: 14 days
- review metrics: 7 days
- monetization offer: 1 day to 7 days depending provider

These are product defaults, not claims about provider update cadence.

## 7.5 Budget guardrails

Project can define:

- maximum paid provider calls;
- maximum estimated spend;
- pause when budget reached;
- warn at 50/80/100%;
- dry-run mode showing expected work before execution.

---

# 8. Job System

Long runs must not execute inside a single web request.

## 8.1 Job types

- `GENERATE_CANDIDATES`
- `RESOLVE_POPULATION`
- `FETCH_SEARCH_VOLUME`
- `FETCH_SERP`
- `FETCH_AUTHORITY`
- `CALCULATE_PRIMARY_GATE`
- `FETCH_SECONDARY`
- `CALCULATE_SECONDARY_SCORE`
- `CHECK_MONETIZATION`
- `EXPORT_RESULTS`

## 8.2 Idempotency

Jobs must be safe to retry.

Each work item uses an idempotency key containing:

- candidate id;
- stage;
- provider;
- relevant configuration hash;
- data freshness bucket.

## 8.3 Failure behavior

Transient provider failures -> retry with exponential backoff and jitter.

Permanent errors -> candidate becomes `ERROR_TERMINAL` for that stage with provider error details.

One candidate failure must not fail the entire project batch.

## 8.4 Progress

Project UI reports:

- total candidate count;
- stage counts;
- current throughput;
- provider error count;
- estimated remaining work;
- cost estimate/actual if supported.

Use polling first; Server-Sent Events or WebSocket can be added later.

---

# 9. Data Model

## 9.1 `projects`

- id UUID
- name
- description
- owner_id future
- active_profile_snapshot JSON
- created_at
- updated_at

## 9.2 `niches`

- id UUID
- parent_id nullable
- level enum: BROAD/MICRO/NANO/SERVICE
- canonical_name
- display_name
- emergency_intent bool nullable
- seasonality_class nullable
- notes

## 9.3 `cities`

- id UUID/internal geography id
- census_geo_id
- name
- state_code
- state_name
- country_code
- population
- population_vintage
- latitude nullable
- longitude nullable
- is_active

Unique: census geo id + vintage semantics as appropriate.

## 9.4 `candidates`

- id UUID
- project_id
- niche_id nullable
- service_term
- city_id nullable
- normalized_keyword
- display_keyword
- language_code
- country_code
- current_status
- automatic_status
- manual_status nullable
- manual_reason nullable
- created_at
- updated_at

Unique within project by normalized candidate identity.

## 9.5 `candidate_events`

Immutable event stream:

- id
- candidate_id
- event_type
- previous_status
- next_status
- reason_code nullable
- payload JSON
- created_at

## 9.6 `keyword_metrics`

- id
- normalized_keyword
- geo_key
- provider
- provider_version nullable
- avg_monthly_searches
- cpc
- competition
- monthly_history JSON
- raw_payload JSON
- fetched_at
- expires_at

## 9.7 `serp_snapshots`

- id
- keyword
- geo_key
- provider
- device
- language
- raw_payload JSON
- fetched_at
- expires_at

## 9.8 `serp_results`

- id
- serp_snapshot_id
- organic_position
- title
- url
- canonical_url
- root_domain
- result_class

## 9.9 `authority_metrics`

- id
- target_type DOMAIN/URL
- target_key
- provider
- da nullable
- pa nullable
- spam_score nullable
- linking_root_domains nullable
- backlinks nullable
- raw_payload JSON
- fetched_at
- expires_at

## 9.10 `candidate_primary_evaluations`

- id
- candidate_id
- profile_snapshot JSON
- population_pass
- sv_pass
- low_da_count
- low_da_required
- da_threshold
- da_pass
- final_primary_pass
- reason_codes JSON array
- evaluated_at

## 9.11 `secondary_metrics`

Flexible table:

- id
- candidate_id
- metric_name
- numeric_value nullable
- text_value nullable
- normalized_score nullable
- source
- raw_payload JSON nullable
- fetched_at

## 9.12 `secondary_scores`

- candidate_id
- score
- completeness
- weight_snapshot JSON
- warnings JSON
- calculated_at

## 9.13 `monetization_offers`

- id
- niche_id nullable
- provider/network
- offer_name
- active
- coverage_type
- geography JSON
- payout
- qualification JSON
- traffic_rules JSON
- source_url nullable
- fetched_at
- expires_at

## 9.14 `runs`

- id
- project_id
- profile_snapshot
- requested_candidate_ids/query
- stage plan
- status
- counters JSON
- estimated_cost nullable
- actual_cost nullable
- started_at
- finished_at

---

# 10. API Design

Base path: `/api/v1`

## Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/{id}`
- `PATCH /projects/{id}`

## Niches

- `POST /projects/{id}/niches/import`
- `GET /projects/{id}/niches`

## Cities

- `GET /cities?min_population=&max_population=&states=`
- `POST /cities/import-census`

## Candidates

- `POST /projects/{id}/candidates/generate`
- `POST /projects/{id}/candidates/import`
- `GET /projects/{id}/candidates`
- `GET /candidates/{id}`

Filters:

- status
- niche
- city/state
- SV range
- low-DA count
- secondary score
- decision

## Runs

- `POST /projects/{id}/runs`
- `GET /runs/{id}`
- `POST /runs/{id}/pause`
- `POST /runs/{id}/resume`
- `POST /runs/{id}/cancel`

## Recalculate

- `POST /projects/{id}/recalculate`

Recalculate must reuse raw metrics where valid.

## Overrides

- `POST /candidates/{id}/override`

Requires reason.

## Exports

- `POST /projects/{id}/exports`
- `GET /exports/{id}`

## SERP Overlay API

- `POST /overlay/metrics`

Input list of visible URLs.
Returns normalized Moz/cache metrics.
Requires NicheForge auth but never exposes vendor secrets.

---

# 11. UI Blueprint

## 11.1 Project Dashboard

Header:

- project name
- profile
- provider health
- budget status
- run status

Funnel cards:

- Input
- Population passed
- SV passed
- SERP fetched
- DA passed
- Deep analysis complete
- Final pass

Main table columns:

- checkbox
- broad/micro/nano niche
- keyword
- city
- state
- population
- SV
- CPC
- trend
- organic result count
- low-DA count
- DA rule (`5 of 10 <10`)
- median PA
- median RD
- Spam Score warning
- local reviews
- secondary score
- completeness
- monetization
- automatic status
- manual status
- last refreshed

Column picker is required because this table will become wide.

## 11.2 Settings Drawer

Primary:

- population min/max
- SV minimum
- DA threshold
- required weak count
- organic depth

Secondary:

- weights
- hard/soft flags
- review thresholds
- trend policy

Providers:

- keyword provider
- SERP provider
- authority provider

Cache:

- freshness policies

Budget:

- call/spend caps

Changing settings must show a preview:

`This change would re-admit 183 SV-rejected candidates. Existing cached SV will be reused.`

## 11.3 Candidate Detail

Tabs:

1. Overview
2. SERP Top 10
3. Authority metrics
4. Secondary analysis
5. Monetization
6. Event history
7. Raw provider evidence

Top-10 view should look like:

| Pos | Result | DA | PA | RD | Spam | Class | Notes |

Rows under DA threshold are highlighted visually.

## 11.4 Ledger

Global searchable ledger across projects:

- candidate
- latest status
- projects used in
- first tested
- last tested
- historical decisions
- stale metrics indicator

Purpose: prevent duplicate manual research.

---

# 12. Chrome Extension — Phase 2

## 12.1 Goal

Show authorized Moz-derived metrics directly beneath Google organic results while the user browses SERPs.

## 12.2 Architecture

Manifest V3 extension consists of:

- content script on supported Google search pages;
- background service worker;
- popup/options UI;
- backend API client.

Chrome Manifest V3 uses service workers for background event handling. Content scripts run in web pages. Treat messages originating from the content script as untrusted; validate URL inputs in the service worker/backend.

## 12.3 Flow

1. content script detects organic-result containers;
2. extract result URL/title;
3. send normalized list to service worker;
4. service worker calls `/api/v1/overlay/metrics`;
5. backend validates host/url;
6. backend uses cache and authorized Moz provider for misses;
7. extension receives only normalized metrics;
8. inject display below blue-link result;
9. MutationObserver handles dynamically inserted results;
10. no vendor key ever reaches page context.

## 12.4 Display

Example:

`DA 7 (Moz) | PA 13 (Moz) | RD 18 | Spam 2%`

Optional profile-aware signal:

`Weak under current profile`

Do not hide raw metrics behind green/red labels.

## 12.5 Accuracy semantics

The extension must show:

- provider label;
- fetched/cached timestamp optionally on hover;
- `N/A` when metric unavailable;
- never substitute another vendor's authority score under a Moz label.

## 12.6 Permissions

Keep permissions minimal:

- storage
- activeTab or host-specific permissions as required
- target Google search hosts
- NicheForge API host

Do not use remote executable code; Manifest V3 extension logic ships inside the extension package.

---

# 13. Secondary Analysis Details

## 13.1 Referring Domains

Preferred metric over raw backlink count for diversity.

Suggested normalization compares Top-10 distribution rather than one absolute universal threshold.

Store median, min, max and quartiles.

## 13.2 Backlinks

Use as context. Detect extreme backlink count with very low DA as possible junk-profile warning, not automatic spam determination.

## 13.3 Spam Score

Provider metric. Never reinterpret as a Google penalty score.

## 13.4 Indexed Pages

Exact Google indexed-page counts are not reliably available as a formal API metric. Treat estimates carefully, record source/method and confidence. This signal remains secondary.

## 13.5 Estimated Traffic

Provider estimates only; label provider.

## 13.6 On-Page Analyzer

Initial automated checks:

- title exists/length;
- service term present;
- location term present;
- meta description exists;
- H1 count;
- service/location in H1;
- content word count;
- heading structure;
- internal links count;
- obvious duplicate title patterns;
- HTTPS;
- basic mobile viewport presence.

Do not claim this reproduces Moz On-Page Score unless Moz data is actually used.

## 13.7 UX Signal

Automated objective signals only in core engine:

- page load timing from a supported performance provider;
- layout/mobile checks;
- CTA/phone-link presence;
- basic accessibility issues.

Qualitative “good design” remains manual/AI-assisted in a later phase and must carry a lower confidence label.

## 13.8 Local Pack Reviews

Store:

- business name
- rating
- review count
- rank

Calculate median/maximum review count. Low reviews are a favorable supporting signal only.

---

# 14. Security

## 14.1 Authentication

MVP can run single-user locally. Cloud version requires authenticated users and project ownership.

## 14.2 Authorization

Every project/candidate/run endpoint checks ownership/workspace membership.

## 14.3 Secrets

Backend only. Environment or managed secrets service.

## 14.4 SSRF prevention

The platform fetches competitor URLs in future on-page analysis. This requires strict SSRF controls:

- allow HTTP/HTTPS only;
- block localhost/private/link-local ranges;
- DNS resolve and validate destination;
- redirect limit;
- response size limit;
- timeout;
- content-type checks.

## 14.5 Extension security

Assume content-script messages can be attacker-influenced. Validate all URLs and commands in service worker/backend. Do not grant content scripts privileged generic proxy functionality.

## 14.6 Provider data retention

Respect vendor terms. Store only permitted raw payloads/derived data. Provider adapters should document retention limitations.

---

# 15. Observability

Structured logs include:

- request id
- project id
- run id
- candidate id
- stage
- provider
- latency
- cache hit/miss
- retry number
- cost estimate if known

Metrics:

- candidates processed/minute
- provider calls
- provider error rate
- cache hit ratio
- funnel survival ratios
- average cost per input candidate
- average cost per final PASS

Health endpoints:

- `/health/live`
- `/health/ready`
- `/health/providers`

Provider health does not expose secrets.

---

# 16. Testing Strategy

## Unit tests

- keyword normalization
- city matching
- population gates
- SV threshold recalculation
- DA count logic
- profile snapshot behavior
- reason codes
- scoring math
- cache freshness
- URL/root-domain parsing

## Provider contract tests

Every provider implementation passes common fixture tests.

## Integration tests

- candidate generation -> population -> SV -> SERP acquisition -> DA primary gate -> deeper SERP analysis -> KD support -> decision using mock providers
- retries
- partial failures
- threshold change and re-admission

## Golden tests

Maintain a fixed set of SERP/metric fixtures with expected primary decisions.

## Extension tests

- extraction against saved Google-result DOM fixtures
- duplicate injection prevention
- dynamic results
- malicious URL/message rejection

## End-to-end acceptance

A project containing a small niche set should produce deterministic PASS/REJECT results using mock providers and remain reproducible after service restart.

---

# 17. Deployment

## Local development

Docker Compose:

- backend
- postgres
- redis
- frontend

Mock providers are default if secrets are absent.

## Small production

- managed PostgreSQL
- managed Redis or equivalent
- backend container
- worker container
- frontend deployment
- HTTPS reverse proxy/platform

## Scaling

Scale workers independently by stage/provider. SERP and authority work are I/O bound.

Rate limits are enforced per provider even when worker count increases.

---

# 18. Repository Structure

```text
nicheforge/
  PROJECT.md
  README.md
  .env.example
  docker-compose.yml
  docs/
    PROJECT_BLUEPRINT.md
    adr/
  backend/
    pyproject.toml
    app/
      main.py
      api/
      core/
      db/
      models/
      schemas/
      providers/
      services/
    tests/
  frontend/
  extension/
  scripts/
```

Provider-specific code must never leak into scoring/business-rule modules.

---

# 19. Phase Roadmap

## Phase 0 — Foundation

- repository
- blueprint
- config
- database
- provider contracts
- mock pipeline

## Phase 1A — Core Validation MVP

- project/candidate APIs
- city import
- generation
- SV provider/import
- SERP provider
- Moz/import adapter
- DA gate
- ledger
- export

## Phase 1B — Production Hardening

- background jobs
- Redis
- retries
- provider throttling
- cost accounting
- auth
- Postgres migrations
- UI dashboard

## Phase 2 — SERP Overlay

- Chrome extension
- backend overlay endpoint
- live DA/PA/RD/Spam display

## Phase 3 — Secondary Intelligence

- RD/backlink depth
- Local Pack/reviews
- traffic
- on-page
- page depth
- EMD/PMD
- trend
- secondary score/completeness

## Phase 4 — Monetization

- network/offer records
- nationwide/ZIP rules
- payout/qualification
- direct buyer support

## Phase 5 — Discovery

- broad-category expansion
- micro/nano suggestion engine
- sibling clustering
- automatic project generation

## Phase 6 — Portfolio Feedback

- site launch records
- ranking/call/revenue outcomes
- predictive calibration from user-owned data

---

# 20. Explicit Non-Negotiable Rules

1. DA primary rule is configurable but cannot be silently bypassed by secondary score.
2. Raw Top-10 results remain inspectable.
3. Any metric labeled Moz must originate from authorized Moz data/import.
4. Population and SV are separate concepts.
5. Nationwide offer availability does not imply national SEO targeting and does not replace local demand validation.
6. Threshold changes recalculate from stored evidence before making new paid calls.
7. Rejected candidates remain in the ledger.
8. All user overrides are audited.
9. No provider secret in browser extension or frontend.
10. No vendor-specific HTTP contract in business-rule code.
11. Missing data is displayed as missing, never imputed silently.
12. Secondary scores always display completeness.
13. The system must be useful with CSV imports even when an API provider is unavailable.
14. Paid API work must be chunked, cached and fail-fast.
15. The project blueprint is updated whenever architecture changes.

---

# 21. Verified External API Constraints Used by This Architecture

These facts were verified against official documentation in August 2026 and should be rechecked when provider adapters are upgraded:

- Google Ads `KeywordPlanIdeaService` supports generating keyword ideas and historical keyword metrics.
- Google Ads keyword-planning methods are separately rate limited; current documentation states a 1 request/second per customer-ID limit for key planning methods.
- DataForSEO Google Organic SERP API supports location-specific result retrieval; its regular task API returns Top-10 results by default.
- DataForSEO keyword endpoints can provide search volume, historical trend, CPC and paid competition depending endpoint.
- Chrome Manifest V3 uses an extension service worker for background behavior and content scripts for page-context interaction.
- Chrome recommends treating content-script messages as untrusted and validating/sanitizing privileged requests.

Provider endpoints, quotas, pricing and field names are not permanent business rules. They must be isolated inside adapters and validated before upgrades.

---

# 22. First Implementation Milestone

The first code milestone is considered successful when this scenario works entirely through mock providers and can then be swapped to live providers:

1. User creates `Pest Control Research`.
2. User imports `rodent control`, `termite control`, `bed bug control`.
3. Engine generates eligible cities using configured 20k–120k population range.
4. Mock/real SV provider returns volume.
5. Rows below configured SV are rejected and preserved.
6. Surviving rows receive localized Top-10 SERPs.
7. Authority provider supplies DA values.
8. Engine counts DA below the selected threshold.
9. Rows with fewer than required weak domains become `PRIMARY_REJECTED`.
10. Survivors appear in a sortable shortlist.
11. User changes SV from 300 to 250 and DA required count from 5 to 4.
12. Engine recalculates from stored evidence without unnecessary provider calls.
13. Results export to CSV.
14. Ledger shows all prior decisions and reasons.

That is the minimum end-to-end product loop. Everything else extends it.
