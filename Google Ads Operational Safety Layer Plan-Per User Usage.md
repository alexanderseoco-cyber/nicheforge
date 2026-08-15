# Google Ads Operational Safety Layer Plan — Per User Usage

## Objective

Add the production-safety layer around the accepted multi-city Search Volume engine without redesigning its batching, cache, FX, evidence, or persistence architecture.

Implementation and validation must use mocks, local databases, fake clocks, and deterministic provider stubs only.

Required external-provider accounting during this phase:

```text
Google Ads: 0
Google customer metadata: 0
FX: 0
SERP: 0
Other providers: 0
```

## Implementation rule

Treat this document as target behavior, not permission to blindly create every proposed model or field. Audit the existing `ProviderCall`, authentication/user model, configuration, transaction infrastructure, deployment topology, and provider boundary first.

Reuse existing models, services, enums, configuration, and transaction infrastructure wherever they already provide the required semantics. If the existing architecture conflicts materially with this plan, stop and report the conflict before redesigning it.

## Phase 1 — Architecture audit

Identify:

- the final Google historical-metrics RPC boundary;
- shared national and multi-city provider paths;
- existing `ProviderCall` model and telemetry;
- retry and error classification;
- customer identity availability;
- current access-level configuration;
- planned versus actual operation accounting;
- current rate-limit and transaction behavior;
- whether the deployment is process-local or distributed.

No code changes or provider requests during the audit.

## Phase 2 — Access-level and production gate

Add explicit configuration only if equivalent controls do not already exist:

```text
GOOGLE_ADS_PRODUCTION_ENABLED=false
GOOGLE_ADS_VERIFIED_ACCESS_LEVEL=UNKNOWN
```

Supported states:

```text
TEST
EXPLORER
BASIC
STANDARD
UNKNOWN
```

Never infer access level from successful requests.

Rules:

- `TEST`: configured test accounts only;
- `EXPLORER`: do not assume KeywordPlanIdeaService production permission;
- `BASIC`: production Keyword Planner requires explicit enablement;
- `STANDARD`: production use remains subject to verified policy;
- `UNKNOWN`: production execution is blocked.

Private deployment and user quota overrides must never bypass provider access restrictions.

## Phase 3 — Actual-attempt ProviderCall telemetry

`ProviderCall` represents an actual provider attempt, not merely planned work. Planned counts belong to the run/batch planning summary.

Persist, where not already supported:

- provider, service, operation;
- run/batch ID;
- safe customer identifier;
- target/geo resource and language;
- chunk index and keyword count;
- attempt number;
- start/end time and duration;
- status and safe error category/code;
- retryable flag;
- provider request ID if safe;
- provider-reached state;
- actual operation consumption;
- cache-saved count.

Never persist secrets, authorization headers, tokens, or unnecessarily large request bodies.

Use explicit semantics such as:

```text
STARTED
PROVIDER_REACHED
SUCCESS
PROVIDER_REJECTED
NETWORK_FAILURE_BEFORE_PROVIDER
FAILED
```

Do not overwrite an earlier failed attempt when a retry succeeds.

## Phase 4 — Three independent accounting ledgers

### Google provider capacity

Track:

```text
verified access level
provider rolling-24-hour limit
actual provider-consumed operations
reserved operations
available provider capacity
```

Use a rolling 24-hour window for provider capacity. Do not treat a calendar-day reset or an assumed Basic quota as verified. If the access level or limit is unknown, return `UNKNOWN`.

### NicheForge user policy

User policy is separate from Google capacity:

```text
default user limit
per-user override
temporary bonus
expiration
```

Recommended model, only if not already represented:

```text
UserProviderQuota
- user_id
- provider
- operation
- daily_limit
- bonus_operations
- effective_from
- expires_at
- override_enabled
- created_by
- created_at
- updated_at
```

Initial values such as 50, 100, and 250 operations must remain configurable policy, not immutable database defaults.

### Per-run budget

Track:

```text
planned initial RPCs
reserved RPCs
actual consumed RPCs
retry allowance
released unused reservation
```

The effective executable allowance is:

```text
min(user remaining allowance, provider currently available capacity)
```

Do not rewrite a user’s configured quota merely because provider capacity temporarily decreases.

## Phase 5 — Atomic reservations

Preview never reserves quota.

The actual Start/Execute operation must atomically reserve its initial planned operations before provider execution begins.

The reservation must prevent concurrent runs from collectively exceeding available capacity:

```text
provider available: 100
run A reservation: 80
run B reservation: 80
invalid total: 160
```

On completion:

- convert consumed operations from reserved to actual;
- release unused reservations;
- reserve additional capacity before retries;
- preserve run accounting after restart.

Use current database transaction/locking infrastructure. Do not add distributed infrastructure unless the deployment topology requires it.

## Phase 6 — Centralized customer rate limiter

All live `GenerateKeywordHistoricalMetrics` calls must pass through one provider-level limiter keyed by Google customer context.

Configuration:

```text
GOOGLE_ADS_KEYWORD_PLANNING_MIN_INTERVAL_SECONDS
```

Google currently documents a Keyword Planning limit of approximately one request per second per CID. NicheForge must enforce a configurable policy at least as conservative as the verified provider requirement. The configured value is implementation policy and must not override Google’s limit.

Requirements:

- no route-level or city-loop sleeps;
- deterministic fake-clock tests;
- no limiter activity during preview;
- no uncontrolled concurrency;
- no open database transaction while waiting;
- honest documentation if the limiter is process-local;
- explicit `RESOURCE_EXHAUSTED` classification.

## Phase 7 — Truthful operation consumption

Distinguish whether Google received the request:

```text
network failure before Google       → consumed = 0
GoogleAdsFailure from Google        → consumed = 1
successful Google response          → consumed = 1
```

Blocked budget checks, local validation errors, previews, and cache hits consume zero provider operations. Each retry is evaluated independently.

## Phase 8 — Zero-network preview

Add or extend a preview endpoint using the exact execution request model and planner/cache identity.

Conceptually:

```text
POST /api/v1/keyword-metrics/research-batch/preview
```

Return:

- submitted keyword count;
- target and language count;
- logical combinations;
- fresh cache hits;
- provider-needed combinations;
- chunk size;
- planned RPC count;
- user remaining operations;
- provider remaining operations when verified;
- access mode and production eligibility;
- budget decision;
- estimated minimum pacing duration;
- `network_requests_made = 0`.

Unknown information must remain `UNKNOWN`, `UNCONFIGURED`, or `UNAVAILABLE`. Preview must never call any provider or reserve quota.

## Phase 9 — Frontend preflight

Show users a concise summary:

```text
Keywords:                    1,000
Cities:                        100
Languages:                       1
Combinations:              100,000
Fresh cache hits:           72,430
Need provider evidence:     27,570
Planned Google operations:      31
Your remaining allowance:      300
Run permitted:                  Yes
Estimated minimum pacing:   ~31 sec
```

Provider-wide capacity may be admin-only. Backend enforcement remains authoritative.

## Phase 10 — Required tests

Add local-only tests for:

- access-level and production gates;
- one ProviderCall per actual attempt;
- retry attempt preservation;
- provider-reached versus pre-provider network failure;
- cache savings;
- same-customer limiter pacing;
- customer isolation;
- atomic concurrent reservations;
- unused reservation release;
- retry reservation enforcement;
- default, overridden, temporary, and expired user quotas;
- effective allowance as the minimum of user and provider capacity;
- all preview planning boundaries;
- all-cached preview with zero planned RPCs;
- 100,000-combination preview with zero network.

Protect the accepted performance properties: no per-result cache lookup, batch-item lookup, FX resolution, flush, commit, or expired-object refresh.

## Phase 11 — Migration and configuration safety

If schema changes are required:

- create an Alembic migration;
- preserve existing records;
- avoid fabricated historical values;
- add only indexes supported by actual rolling-window and user-quota queries;
- document every new environment variable, default, unset behavior, and whether it is product policy or provider metadata.

## Phase 12 — Validation

Run operational tests, existing multi-city tests, Search Volume tests, currency/FX tests, Commercial Insights tests, Rank & Rent tests, Python compilation, frontend TypeScript, migration upgrade, and `git diff --check`.

Required network result:

```text
Google Ads: 0
Google customer metadata: 0
FX: 0
SERP: 0
Other providers: 0
```

Do not commit automatically. Report architecture audit, files changed, telemetry semantics, limiter behavior, three-ledger accounting, reservation behavior, preview contract, tests, static validation, network accounting, performance regression status, and remaining limitations for review.

## Acceptance condition

Before a live run, NicheForge must truthfully show combinations, cache savings, provider-needed work, planned RPCs, access eligibility, user allowance, provider capacity when verified, reservation status, and pacing estimate.

After execution, it must show actual attempts, provider reach, success/failure/retry states, consumed operations, released reservations, target/language/chunk identity, and cache savings.
