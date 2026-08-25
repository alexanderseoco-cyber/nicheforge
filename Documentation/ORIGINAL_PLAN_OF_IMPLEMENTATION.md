# Original Plan of Implementation

**Project:** NicheForge — Rank & Rent Niche Intelligence Engine  
**Phase:** Phase 1A — Durable Mock-Provider Validation Core  
**Status:** Approved; pre-implementation inspection authorized  
**Authority:** `PROJECT.md` and `docs/PROJECT_BLUEPRINT.md`

## Checkpoint status

- **Checkpoints A–F:** Complete and approved. Historical implementation details remain recorded in `Task completion.md/STATUS.md`.
- **Provider Readiness & Live Integration Boundary:** Complete for the deterministic/mock/Sandbox boundary and approved as the current implementation state.
- **Live provider activation:** Deferred until current official contracts, credentials, quotas, billing, rate limits, and paid-call approval are verified. Moz remains unverified and is not enabled as a live dependency.
- **Next authorized work:** Provider-contract verification and safe live-integration preparation only; no broad paid production run is authorized.

This document is the approved implementation plan for Phase 1A and is part of the required NicheForge project workflow.

## Workflow gate

The sequence is:

1. Establish the supplied scaffold and record the baseline.
2. Inspect the repository, Git state, local dependency policy, and runtime environment.
3. Produce the pre-implementation schema report.
4. Obtain approval for the concrete schema and migration strategy.
5. Implement the durable persistence foundation.
6. Implement intake, evidence-backed gates, runs, recalculation, ledger, imports, and exports.
7. Expand tests and execute the complete mock-provider acceptance flow.
8. Report actual validation results and remaining blockers.

No schema migration or substantive model/pipeline implementation may begin before the pre-implementation report is approved.

## Task completion synchronization

Every new change, completed task, milestone, or blocked task must update `Task completion.md/STATUS.md`. Each update must record the work completed, files changed, validation actually executed, remaining work or blockers, and the related phase or milestone in this plan.

After each update, reconcile this plan so its phase status reflects the actual repository state. A phase may only be marked implemented or complete after its required work and validation have actually been completed. Never record a test, build, migration, or environment check as successful unless it executed successfully.

## Approved architectural requirements

- Separate global logical candidate identity from project-candidate membership.
- Use append-only/versioned provider evidence; refreshes create new evidence versions.
- Keep mutable cache pointers separate from immutable evidence referenced by historical runs.
- Cache freshness affects future execution but never rewrites historical decisions.
- Preserve every generated candidate, including population, SV, SERP, and DA rejects.
- Keep primary gates separate from secondary signals and monetization.
- Phase 1A `PASS` means all currently enabled required primary gates passed; it does not mean commercial validation is complete.
- Treat API, CSV, and manual evidence as first-class sources with explicit provenance.
- Record provider calls and stage-level costs, including zero-cost mock calls.
- Enforce fail-fast processing: upstream rejection prevents downstream provider work until recalculation or authorized refresh re-admits the candidate.
- Keep provider-specific HTTP and parsing behind provider abstractions.
- Do not invent or finalize an unverified Moz API contract.
- Keep project-installed dependencies, environments, caches, local data, and generated development artifacts inside the project root.

## Phase 1A scope

- Alembic migrations and durable SQLite/PostgreSQL-compatible persistence.
- Projects, cities, logical candidates, project memberships, runs, run participants, events, evidence, cache metadata, imports, exports, provider calls, and costs.
- Candidate and city CSV imports.
- Deterministic mock-provider validation from population through primary DA decision.
- Append-only evidence and immutable historical run references.
- Threshold recalculation using stored evidence before new provider calls.
- Ledger and decision history queries.
- CSV result export.
- Unit, integration, persistence, determinism, fail-fast, cost, and acceptance tests.

## Explicitly deferred

Unless required for compatibility, Phase 1A will not implement live Moz integration, production DataForSEO batching and billing, secondary competitor intelligence, monetization integrations, authentication, production Redis orchestration, competitor crawling, full frontend redesign, or Chrome extension hardening.

## Required pre-implementation report

Return the following and then stop for approval:

1. Extracted repository tree and active-workspace confirmation.
2. Git status/baseline and `.gitignore` issues.
3. Python, Node, npm, Docker, and Compose availability and versions.
4. Existing database schema reconstructed from code.
5. Concrete Phase 1A schema with columns, keys, constraints, and indexes.
6. Existing-to-proposed model mapping and data-preservation strategy.
7. Alembic migration strategy.
8. Candidate identity algorithm.
9. Evidence versioning and cache-key strategy.
10. Run, run-participant, and event immutability strategy.
11. Provider-call and cost model.
12. Recalculation and evidence-reuse strategy.
13. Exact files expected to change.
14. Detailed test implementation plan.
15. Contradictions, migration risks, data-loss risks, dependency issues, and blockers.

Do not modify `PROJECT_BLUEPRINT.md` merely to accommodate scaffold code. Genuine deviations require a proposed and approved ADR.

## Current Reconciliation — Provider Readiness Current State

Checkpoints A–F are complete and approved. Provider Readiness is complete for the deterministic boundary and is the current project state. The stale historical checkpoint entries near the top are superseded by the checkpoint status above; implementation history remains preserved in `Task completion.md/STATUS.md`. Live activation remains deferred pending verified provider contracts and explicit approval.

## Provider Readiness & Live Integration Boundary

The next authorized checkpoint is provider readiness only. Its credential and paid-call rules are defined in `docs/API_KEYS_AND_PROVIDER_ACCESS_RULES.md`. It must verify official provider contracts, mode separation, budget approval, source-policy selection, adaptive DA semantics, and safe evidence mapping before live calls. No broad paid production run is authorized.

## Google Ads Operational Safety Layer — approved next checkpoint

The accepted multi-city Search Volume scaling and 100,000-combination
performance work is complete. The next checkpoint is operational safety only,
as documented in `Google Ads Operational Safety Layer Plan-Per User Usage.md`.

The implementation must begin with an audit of existing ProviderCall,
authentication/user, configuration, transaction, and deployment infrastructure.
Existing abstractions must be extended rather than duplicated. If a material
architectural conflict is found, implementation must stop and report it before
redesign.

The approved scope includes explicit Google access-level gating, actual-attempt
ProviderCall telemetry, rolling-24-hour provider capacity, separate NicheForge
user quotas, per-run budgets, atomic concurrent reservations, centralized CID
rate limiting, truthful provider-reached operation accounting, and a
zero-network preview endpoint/UI.

The effective executable allowance is the minimum of current user allowance
and currently available provider capacity. This does not mutate the configured
user quota when provider capacity changes.

Phase 1 audit and Phase 2 access-gate implementation are complete. The audit
confirmed that no authentication/user model exists, Google Search Volume
ProviderCalls are not yet persisted at the multi-city boundary, and current
access/quota metadata is not locally verified. Explicit production gating was
added using verified access levels; per-user quota and reservation work remains
deferred until a real user identity boundary is available.

Phase 2 validation: 15 targeted tests passed, Python compilation passed,
`git diff --check` passed, and all external-provider requests remained zero.

Implementation and validation must make zero external provider requests. No
automatic commit is authorized. Phase status remains implementation pending
until the architecture audit and subsequent validations actually pass.

Phase 3 actual-attempt telemetry has now been implemented at the existing
multi-city provider chunk boundary. ProviderCall records are created only for
actual chunk attempts, with a pre-transport STARTED record, execution mode,
customer/target/language/chunk metadata, attempt number, duration,
provider-reached classification, actual operation count, outcome, and
sanitized failure details. Planned RPC counts remain planning/report data and
are not treated as consumed provider operations. The additive migration is
`c11providercalltelemetry`, based on `c10derivedmetrics`.

Phase 3 validation so far: 10 focused multi-city tests passed, no provider
requests were made, and `git diff --check` passed. Compilation was attempted
but existing locked `__pycache__` files prevented replacement of generated
bytecode; this is an environment/file-lock condition, not a reported source
syntax failure. Single-keyword telemetry, rate limiting, operation budgets,
and preview remain subsequent Phase 3 work.

Single-keyword research telemetry is now covered as well. The standalone
research route passes its database session and customer context into the
provider-agnostic batch orchestrator, which persists one actual-attempt
ProviderCall per provider chunk. Mock execution is marked MOCK with zero
consumed operations. API/provider and multi-city telemetry tests pass with
zero external requests. Rate limiting, operation budgets, and preview remain
the next operational safeguards.

The zero-network planning preview has been extended to expose total logical
combinations, fresh-cache savings, provider-required work, target/language
counts, chunk size, planned RPC count, operation-budget status, remaining
provider capacity, and effective executable allowance. A local provider
telemetry summary endpoint reports persisted actual attempts, outcomes,
consumed operations, and submitted keyword counts without transport. Preview
and telemetry API tests pass with zero external requests. The next step is a
full focused regression and checkpoint review for the operational safety
layer.

The next approved milestone is documented in `Authentication User Identity
Foundation.md`. It adds only durable local user identity and authentication
above the committed provider-safety layer. Access-token and refresh-session
lifetimes are configurable; refresh tokens are hashed, rotated, and checked
for revocation server-side. Roles remain `ADMIN`/`USER`, user IDs remain the
future quota key, and the last active administrator is protected. Per-user
quotas, bonuses, reservations, billing, and provider allocation remain out of
scope. Implementation must remain zero-network and uncommitted until review.

Final Phase 3 hardening uses a rolling 24-hour provider-operation window, not
calendar-day accounting. In addition, production-enabled Google transport is
blocked unless the configured customer rate limiter is enabled. This prevents
an accidental production configuration from running Keyword Planner calls
without pacing. Both behaviors are covered by deterministic tests with zero
provider requests.

The configurable operation-budget guard is now implemented. An unset daily
budget is explicitly `UNKNOWN_UNVERIFIED` and does not block execution. When
configured, the guard atomically counts one operation per attempted Google
RPC, scoped by customer and UTC day; it never counts keywords or planned
combinations. Exhaustion is rejected before provider transport and recorded as
`BUDGET_EXCEEDED`, distinct from provider rejection and pre-provider network
failure. The focused rate-limit/budget/API/multi-city suite has 25 passing
tests with zero external requests. Capacity telemetry reconciliation and the
public zero-network preview remain next.

The centralized customer rate limiter is now implemented at the Google Ads
provider invocation boundary. It is disabled by default, configurable by
requests per second, and serializes calls per customer without coupling
different customers. Deterministic tests verify same-customer spacing,
customer isolation, and disabled zero-wait behavior. No provider requests were
made. The next safeguard is the configurable operation-budget guard; quota
must count actual attempts rather than planned keyword combinations.

Authentication implementation has started after the provider-safety commit.
The audit found no existing identity framework, so the foundation reuses the
current FastAPI/SQLAlchemy conventions with local PBKDF2-HMAC password
hashing, configurable short-lived signed access tokens, and hashed rotating
refresh sessions. Migration `c12authidentity` follows
`c11providercalltelemetry`. Initial local tests cover login, refresh
rotation/revocation, disabled-user rejection, and last-active-admin safety.
Search Volume routes remain staged during frontend integration rather than
being silently broken. No provider calls are authorized in this phase.

The remaining foundation work is complete pending review: frontend login and
session-aware API client, separate authentication-attempt limiting, ADMIN-only
provider telemetry, and isolated `c12authidentity` migration validation are
implemented. Search Volume execution remains staged for authenticated rollout
after frontend integration so existing local anonymous workflows are not
silently broken. Focused authentication/provider tests pass with zero network
requests; per-user quotas and reservations remain a future phase.

## Final infrastructure phase — per-user quotas and atomic reservations

The authentication foundation is complete. This checkpoint extends it with
UserProviderQuota, immutable expiring UserQuotaBonus, RunReservation, and
UserProviderUsage. ProviderCall operation counts remain authoritative for
external consumption; usage is attribution only. Reservations are atomic,
preview is non-mutating, unused capacity is released, and retries require
additional atomic capacity. Search Volume routes derive identity only from the
authenticated dependency. No billing or subscriptions are included. Work and
validation are zero-network and uncommitted; after acceptance, Phase 3 Rank &
Rent Engine resumes.

## UI/UX redesign reconciliation

The detailed frontend roadmap is maintained in
`NicheForge UI UX Redesign Roadmap.md`. The app shell is complete; Search Volume
workspace functionality is substantially complete; authentication and
allowance feedback are the current integration boundary; and the next product
phase is the Rank & Rent Engine/UI. Future UI work must preserve evidence
immutability, policy separation, explicit partial/unavailable states, and
zero-network preview behavior.
