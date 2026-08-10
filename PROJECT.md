# NicheForge

**Product name:** NicheForge  
**Product class:** Rank & Rent Niche Intelligence Engine  
**Tagline:** Find. Validate. Rank.  
**Status:** Architecture locked; Phase 1 MVP scaffold included in this repository.  
**Primary source of truth:** `docs/PROJECT_BLUEPRINT.md`  
**Decision precedence:** Blueprint > accepted ADRs > code > comments > chat history.

---

## 1. Mission

NicheForge converts large, messy local-service niche pools into a small set of evidence-backed Rank & Rent opportunities by applying a staged, configurable validation funnel.

The business-priority workflow is:

`niche input -> city generation/import -> population filter -> search-volume filter -> DA competition gate -> deeper SERP analysis -> KD support/prioritization -> current result/history -> monetization checks -> live shortlist/ledger`

Technically, DA competition evaluation requires a localized SERP acquisition first: `population -> SV -> SERP acquisition -> DA primary gate -> deeper SERP analysis -> KD -> result/history`. SERP acquisition (retrieving the organic competitor set) is distinct from deeper SERP analysis. Population, SV, and DA are the central validation criteria; KD is later and supportive.

NicheForge is deliberately not a generic SEO suite. It is a workflow engine for local Rank & Rent niche validation.

---

## 2. Core Product Principles

1. **Primary gate before secondary scoring.** A candidate that fails the configured low-DA Top-10 rule is rejected even if secondary metrics look attractive.
2. **No hard-coded instructor thresholds.** Defaults may match the working method, but population, SV, DA threshold, required low-DA count, KD, review count and secondary weights must be user-configurable.
3. **Fail fast to control cost.** Do not request expensive downstream data for candidates already rejected upstream.
4. **Provider independence.** Search volume, SERPs, authority metrics, reviews and monetization data are accessed through provider interfaces so vendors can be replaced.
5. **Raw evidence is always visible.** Scores never replace the underlying DA, PA, RD, backlinks, SV, CPC, trend and SERP rows.
6. **Reproducibility.** Every run stores settings, provider versions, timestamps and reason codes.
7. **Caching first.** Reuse domain and keyword metrics whenever freshness policy permits.
8. **Manual override without silent mutation.** Users can override a decision, but the automatic decision and override reason must both remain recorded.
9. **No scraping of authenticated vendor UIs as the default architecture.** Prefer authorized APIs, official exports or explicitly supported integrations.
10. **The niche ledger is permanent.** Previously tested niche/city combinations must not be accidentally repeated unless the user explicitly reruns them.

---

## 3. Default Validation Profile

The default profile reflects the workflow currently being used but is not hard-coded:

- Population minimum: `20,000`
- Population maximum: `120,000`
- Minimum local search volume: `300`
- User may lower or raise SV before a run or dynamically after results appear
- Weak-domain DA threshold: `< 10`
- Minimum weak domains in organic Top 10: `4` (PASS)
- Ideal weak domains in organic Top 10: `5` (IDEAL; 5+ remains IDEAL)
- Authority evaluation mode: `ADAPTIVE` by default; `FULL` configurable
- Organic result depth: `10`
- KD: optional / secondary in initial implementation
- Keyword Difficulty provider: Moz by default when enabled
- Preferred KD threshold: `< 15` by default, configurable
- KD mode: `PRIORITY` by default; optional `HARD_GATE`
- Non-seasonal demand: preferred, warning by default
- Nationwide monetization: preferred, not an automatic SEO gate
- Low local review counts: supporting signal only
- Indexed pages, referring domains, backlinks, page authority, spam score, UI/UX, on-page strength and estimated traffic: secondary signals

A candidate may only become an automatic **PASS** when all configured primary gates pass. DA classification is `0–3 = PRIMARY_REJECTED`, `4 = PASS`, and `5+ = IDEAL`; minimum and ideal counts are independently configurable and snapshotted per Run.

Keyword Difficulty is keyword-level, provider-specific evidence evaluated after the DA primary gate. Moz KD is the default source and `<15` is the default preferred threshold, but the threshold and mode are user-configurable. In `PRIORITY` mode, KD classifies DA-qualified candidates as `IDEAL` or `ABOVE_PREFERRED` without overriding the decisive DA gate. In `HARD_GATE` mode, candidates at or above the configured threshold may be rejected with `KD_ABOVE_THRESHOLD` only after passing DA. Excellent KD never overrides failed DA.

Changing only the KD threshold must recalculate from compatible stored KD evidence without a new provider request. Moz KD evidence remains separate from DA/PA authority evidence. A single provider request may produce both SV and KD evidence only when the authorized provider contract actually returns both; cost attribution must not duplicate that provider call. The project must not assume that Moz KD and Moz authority metrics share an endpoint or have zero incremental cost until the authorized Moz contract is verified.

---

## 4. Product Modules

### Phase 1 — Validation Engine MVP

- Project creation
- Niche/category/micro/nano input
- CSV/XLSX/text import
- U.S. city master dataset import
- Population-based city generation
- Unlimited logical keyword input; processing is chunked internally
- Search-volume provider abstraction
- Configurable SV threshold
- Localized Google organic SERP retrieval
- Top-10 domain extraction and normalization
- Moz metrics provider abstraction
- DA/PA and link metrics ingestion
- Configurable DA threshold and weak-site count
- Primary gate engine
- Rejection reason codes
- Live progress/status table
- CSV export
- Persistent ledger and cache

### Phase 2 — Live SERP Overlay

Chrome Manifest V3 extension:

- Detect organic Google results
- Extract visible URLs
- Query NicheForge backend
- Show Moz DA/PA and optional Spam Score / RD beneath results
- Cache results
- Clearly label metric provider
- Never embed API secrets in the extension

### Phase 3 — Deep Validation

- Referring domains
- Backlinks
- Spam Score
- Page Authority
- Estimated competitor traffic
- Indexed-page estimates
- EMD/PMD classification
- Local Pack / review analysis
- Basic on-page weakness scanner
- UI/UX review hooks
- Trend/seasonality analysis
- Secondary weighted score
- Data-completeness score

### Phase 4 — Monetization Intelligence

- Offer provider interfaces
- Nationwide / ZIP / state-specific classification
- Payout
- Call-duration / appointment qualification
- Allowed traffic sources
- Active/inactive state
- Direct buyer prospect research/import
- Monetization recheck before final approval

### Phase 5 — Discovery Automation

- Accept broad categories such as `pest control`
- Generate micro/nano candidates from approved sources/providers
- Categorize sibling services
- Build topical families
- Generate city combinations automatically
- Run the validation funnel without manual handoffs

### Phase 6 — Portfolio & Learning Layer

- Track built sites
- Rank/call/revenue outcomes
- Compare predicted opportunity vs. real outcomes
- Refine secondary scoring weights from user-owned historical data
- Never automatically weaken the configured primary DA gate unless the user explicitly changes it

---

## 5. Canonical Status Model

Every candidate is always in exactly one workflow status:

- `IMPORTED`
- `POPULATION_PENDING`
- `POPULATION_REJECTED`
- `SV_PENDING`
- `SV_REJECTED`
- `SERP_PENDING`
- `SERP_FETCHED`
- `AUTHORITY_PENDING`
- `PRIMARY_REJECTED`
- `SECONDARY_PENDING`
- `SECONDARY_COMPLETE`
- `MONETIZATION_PENDING`
- `WATCHLIST`
- `PASS`
- `MANUALLY_REJECTED`
- `MANUALLY_APPROVED`
- `ERROR_RETRYABLE`
- `ERROR_TERMINAL`

The system must preserve previous transitions in an immutable event log.

---

## 6. Canonical Rejection Reason Codes

- `POPULATION_BELOW_MIN`
- `POPULATION_ABOVE_MAX`
- `SV_BELOW_THRESHOLD`
- `SV_MISSING`
- `SV_PROVIDER_CONFLICT`
- `SERP_INSUFFICIENT_ORGANIC_RESULTS`
- `LOW_DA_COUNT_BELOW_REQUIRED`
- `MONETIZATION_GEO_UNSUPPORTED`
- `MONETIZATION_INACTIVE`
- `SEASONALITY_HARD_GATE`
- `MANUAL_REJECT`
- `PROVIDER_ERROR`

Secondary warnings include:

- `HIGH_MEDIAN_RD`
- `HIGH_MEDIAN_PA`
- `HIGH_SPAM_SCORE`
- `STRONG_LOCAL_PACK_REVIEWS`
- `HIGH_INDEXED_PAGE_FOOTPRINT`
- `STRONG_ONPAGE_COMPETITORS`
- `STRONG_UI_UX_COMPETITORS`
- `SEASONALITY_WARNING`
- `NO_NATIONWIDE_OFFER`
- `DATA_INCOMPLETE`

---

## 7. Technology Baseline

- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL in production; SQLite allowed for local development only
- **ORM:** SQLAlchemy 2.x
- **Migrations:** Alembic
- **Background jobs:** Redis + RQ/Celery (Phase 1.1); synchronous fallback for local dev
- **HTTP:** httpx
- **Validation:** Pydantic 2.x
- **Frontend:** Next.js + TypeScript (Phase 1 UI)
- **Chrome extension:** Manifest V3 + TypeScript
- **Containerization:** Docker Compose
- **Tests:** pytest

---

## 8. External Data Strategy

NicheForge must not depend on one vendor.

### Population

Primary: U.S. Census incorporated-place dataset, imported locally and versioned.

### Search Volume

Supported architecture:

- Google Ads API historical metrics
- DataForSEO keyword-data / historical search volume
- CSV import from Keywords Everywhere
- CSV import from Ahrefs

Google Ads API requires Google Ads authentication/developer access, not merely a simple API key. Keyword planning methods are separately rate limited; therefore the provider layer must batch and throttle requests.

### SERP

Default recommended programmatic provider: DataForSEO Google Organic SERP API or another provider implementing the same internal interface.

### Moz Metrics

NicheForge must use authorized Moz API/data access or user-provided Moz exports. Do not make authenticated Moz UI scraping the architectural dependency. Exact Moz endpoint details live in the provider adapter and configuration rather than the scoring engine.

---

## 9. Secrets

Secrets may only live in environment variables or a secrets manager.

Never commit:

- Google Ads OAuth credentials
- Google Ads developer token
- DataForSEO username/password
- Moz API credentials
- database production password
- JWT/signing secrets

The Chrome extension must never contain vendor secrets. It only calls the NicheForge backend.

---

## 10. Definition of Done — Phase 1 MVP

Phase 1 is complete only when a user can:

1. create a project;
2. paste/upload one or more niches;
3. select a population range;
4. generate/import city-keyword combinations;
5. choose an SV threshold;
6. run SV filtering;
7. retrieve localized organic Top 10 for survivors;
8. retrieve/import Moz DA metrics for Top-10 domains;
9. configure DA threshold and required low-DA count;
10. see automatic pass/reject outcomes with reason codes;
11. alter the SV or DA settings and recalculate without losing raw data;
12. export the results;
13. see previously processed candidates in the ledger;
14. rerun stale data intentionally;
15. run the automated test suite successfully.

---

## 11. Non-Goals for MVP

- Automatic website creation
- Backlink building
- Rank manipulation
- Automatic outreach
- Fully autonomous niche discovery
- Recreating Moz DA with a home-grown approximation
- Scraping authenticated Moz/Ahrefs/SEMrush user interfaces

---

## 12. Original Plan of Implementation

The approved implementation workflow is maintained in [`docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md`](docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md). It is a required project artifact alongside this document and `docs/PROJECT_BLUEPRINT.md`.

Before substantive implementation, the agent must complete the extraction, baseline, environment, repository, and schema inspection described there and return the pre-implementation report for approval. Schema migrations and Phase 1A model/pipeline changes must not begin before that approval.

All project-installed dependencies, virtual environments, package installations, dependency caches, local databases, test data, build artifacts, and generated development files must remain inside the NicheForge project root. Python must use a project-local `.venv`; frontend dependencies must use project-local `node_modules`; project configuration must not place project dependencies in a separate `C:\` directory.

## 12.1 Verified Development Environment

The verified Python runtime for this project is:

```text
D:\Python312\python.exe
Python 3.12.10
```

Use this interpreter to create the project-local environment at `.venv`. Install project packages into that local environment only; do not install them globally. The Windows `py` launcher may not enumerate this installation reliably in every shell, so the exact executable path above is the authoritative Python 3.12 path for project setup.

## 13. Task Completion and Plan Reconciliation

Every new change, completed task, milestone, or blocked task must automatically update [`Task completion.md/STATUS.md`](Task%20completion.md/STATUS.md). The status update must record the work completed, files changed, validation actually executed, remaining work or blockers, and the corresponding phase or milestone reconciled in [`docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md`](docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md).

The task status and original implementation plan must remain synchronized. A phase may not be marked implemented or complete until its required work and validation have actually been completed. No test, build, migration, or environment check may be recorded as successful unless it executed successfully.

## 14. Engineering Rule

If code, implementation shortcuts or future chat instructions conflict with `docs/PROJECT_BLUEPRINT.md`, the blueprint wins unless an explicit ADR changes it.
