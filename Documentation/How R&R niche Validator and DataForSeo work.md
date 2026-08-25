# How Rank & Rent Niche Validator and DataForSEO Work

## Purpose

NicheForge validates Search Volume handoffs through an evidence-first workflow. It supports two independent scopes:

- **Local Rank & Rent** — city-based validation.
- **General Niche** — national/general keyword validation without city population filtering.

Provider evidence is persisted, attributed to its source, and shown only when it exists. Missing evidence is displayed as **Not available**, never as zero.

## End-to-end workflow

```text
Search Volume
  → handoff
  → project resolution/creation
  → ProjectCandidate attachment
  → zero-network preview
  → user starts validation
  → SERP collection
  → authority evidence
  → optional deeper enrichment
  → KD
  → final candidate result
```

### 1. Search Volume handoff

Search Volume creates immutable keyword evidence containing the submitted keyword, search volume, provider, country, language, and targeting context.

When the user sends results to Rank & Rent:

- only evidence selected from the current Search Volume result set is sent;
- stale selections from previous research batches are cleared;
- each handoff keeps its own `handoff_id` and evidence ID;
- the original Search Volume targeting remains truthful.

The handoff does not perform SERP, Moz, Ahrefs, or backlink work.

### 2. Scope classification

Each handoff is classified independently.

#### Local Rank & Rent

Used when a city/location is explicitly targeted or the keyword requires local resolution.

```text
Population → Search Volume → Local SERP → Authority → Deep Analysis → KD → Result
```

#### General Niche

Used for general keywords such as `stylish text generator` or `fancy text generator`.

```text
Search Volume → National SERP → Authority Opportunity → Deep Analysis → KD → Result
```

General candidates have:

- no city prompt;
- population status `NOT APPLICABLE`;
- national country targeting;
- independent readiness from local candidates.

### 3. Project and candidate attachment

The Validator resolves or creates a project, then attaches each handoff to a `ProjectCandidate`.

The attachment preserves:

- CandidateEntity identity;
- validation scope;
- Search Volume evidence lineage;
- selected city identity where required.

Historical projects are not silently reused for new batches. A fresh handoff batch creates a fresh project unless an existing project is explicitly supplied.

Ambiguous local cities produce a location-confirmation state. The system does not guess between cities with the same name.

### 4. Zero-network validation preview

Preview is a planning step. It does not call providers.

It reports:

- candidate count;
- reusable Search Volume evidence;
- estimated provider work;
- scope-specific policies;
- expected downstream stages;
- `preview_network_requests = 0`.

Start Validation is enabled only after the backend confirms executable ProjectCandidates.

## Provider responsibilities

| Provider | Evidence | Normal role |
|---|---|---|
| Google Ads / keyword metrics provider | Search volume and keyword metrics | Search Volume and reusable SV evidence |
| DataForSEO SERP | Organic positions, domains, URLs | Local or national SERP collection |
| Moz | DA, PA and related authority evidence | Existing authority stage and Local DA policy |
| Ahrefs | Domain Rating (DR) | Separate authority signal and General Niche opportunity input |
| DataForSEO Backlinks | Referring domains, backlinks and related metrics | Optional Deep Analysis enrichment |

Provider metrics are never silently merged. DA/PA remain Moz metrics, DR remains Ahrefs, and backlink metrics remain DataForSEO metrics.

## Normal validation execution

After a valid SERP response:

1. SERP domains are normalized and deduplicated.
2. Each SERP row retains its position and exact URL.
3. Moz authority evidence is reused or fetched according to freshness policy.
4. Ahrefs DR is reused or fetched when its feature flags and approval are enabled.
5. The existing Local DA gate remains unchanged.
6. General Niche opportunity can use DA and DR together.
7. Optional DataForSEO Backlinks enrichment runs only after earlier qualification.
8. KD runs according to the configured KD policy.
9. The final result and all captured evidence are persisted.

## Ahrefs DR

Ahrefs DR is wired for future and current approved runs.

Configuration fields:

- `ahrefs_proxy_enabled`
- `ahrefs_live_approved`
- `ahrefs_api_key`
- `ahrefs_api_base_url`
- `ahrefs_domain_rating_path`

The adapter uses Ahrefs’ Domain Rating endpoint. DR evidence is stored separately from Moz authority evidence and linked through:

```text
RunCandidate
  → SERP result row
  → ProxyAuthorityEvidence
```

The API exposes `ahrefs_dr` and `dr_provider`. The frontend displays missing DR as `Not available`.

Historical runs are not rewritten automatically. They require an authorized enrichment or rerun.

## DataForSEO Backlinks enrichment

DataForSEO backlink enrichment is optional because it creates additional provider usage and cost beyond SERP requests.

The existing endpoint is:

```text
POST /v3/backlinks/bulk_pages_summary/live
```

Available factual fields include:

- `referring_domains`;
- `referring_main_domains`;
- `referring_ips`;
- `referring_subnets`;
- `backlinks`;
- `backlinks_spam_score`.

### Enrichment policy

NicheForge uses a conservative targeted policy:

- SERP must succeed first.
- The candidate must reach the deeper-analysis path.
- Only weak/interesting domains are selected by default.
- Domains are deduplicated before lookup.
- Local candidates retain the existing DA hard gate.
- General candidates can continue after authority opportunity grading.
- Backlink metrics are advisory evidence, not pass/fail gates.

The current feature flags are:

- `dataforseo_backlink_proxy_enabled`
- `dataforseo_backlink_live_approved`
- `dataforseo_backlink_budget`
- `dataforseo_backlink_batch_size`

If the feature is disabled, unapproved, over budget, or not executed, the UI displays backlink fields as `Not available`.

### Cost behavior

Backlink enrichment is separate from the SERP request and can consume additional DataForSEO budget. Cost depends on:

- number of selected domains;
- fresh lookups versus cache hits;
- endpoint pricing;
- configured batch and budget limits.

Cache and budget guards prevent uncontrolled usage. Opening an old run or expanding a domain row does not make a provider request.

## Evidence lineage

The canonical domain evidence relationship is:

```text
RunCandidate
  → SerpResultRow
  → Moz AuthorityEvidence
  → Ahrefs ProxyAuthorityEvidence
  → DataForSEO ProxyBacklinkFeatureEvidence
```

The Ahrefs and backlink links use explicit database link records. They do not depend on array position, display order, or keyword text matching.

## API and UI presentation

Each domain row can expose:

- position;
- domain and URL;
- Moz DA/PA;
- Ahrefs DR;
- referring domains;
- backlinks;
- provider attribution;
- evidence signal.

The main table uses one semantic row per domain and one cell per metric:

```text
Position | Domain | DA | PA | DR | RDs | Backlinks | Signal | Actions
```

Expanded details can show:

- SERP position and URL;
- Moz DA/PA;
- Ahrefs DR;
- DataForSEO referring domains and main domains;
- referring IPs/subnets;
- backlinks;
- backlink spam score;
- provider provenance.

No expanded detail interaction triggers network work.

## Missing and partial evidence

Evidence states are factual:

- `COMPLETED`
- `PARTIAL`
- `RETRYABLE`
- `NOT RUN`
- `NOT AVAILABLE`

Examples:

- 10 SERP results and 0 DR records → DR coverage `0/10`, values `Not available`.
- 10 SERP results and 7 DR records → DR coverage `7/10`; the remaining three are unavailable.
- 9 SERP results when 10 were required → SERP coverage `9/10`, status `PARTIAL` or `RETRYABLE`; all nine rows remain visible.

Missing evidence is never represented as numeric zero.

## General Niche authority grading

For General Niche candidates, the configured initial weakness signals are:

- DA `< 20`;
- DR `< 20`.

The same domain is counted only once when either metric is weak.

| Unique weak domains | Classification |
|---:|---|
| 4+ | `STRONG_POTENTIAL` |
| 3 | `GOOD_POTENTIAL` |
| 1–2 | `POTENTIAL_NICHE` |
| 0 | `LOW_AUTHORITY_OPPORTUNITY` |

RDs and backlinks are not classified as weak or strong unless a separate policy threshold is explicitly configured.

## Safety rules

- Preview makes zero provider calls.
- Unit and focused integration tests use mocks/local evidence.
- Provider credentials are never displayed in logs or UI.
- New batches do not silently reuse historical projects.
- Evidence conflicts do not overwrite immutable lineage.
- Reruns preserve the evidence attached to earlier RunCandidates.
- Provider work is gated by feature flags, approval, cache, quota, and budget rules.
- No provider request occurs merely because a user opens a historical run or expands details.

## Operational procedure

1. Run Search Volume research.
2. Select the current evidence rows.
3. Send to Rank & Rent.
4. Resolve a city only when the local scope requires it.
5. Confirm project and candidate readiness.
6. Review zero-network Preview.
7. Start validation once executable candidates are confirmed.
8. Review candidate-specific pipeline status.
9. Review coverage and domain evidence.
10. Expand details for provider-level evidence.
11. Enable or authorize DataForSEO Backlinks only when deeper enrichment is justified.
12. Review cost, coverage, and provider attribution.

## Current interpretation of unavailable metrics

If the Validator shows:

```text
Ahrefs DR: Not available
RDs: Not available
Backlinks: Not available
```

that means the current run has no persisted evidence for those fields. It does not mean the metric value is zero and does not necessarily indicate a code defect.

