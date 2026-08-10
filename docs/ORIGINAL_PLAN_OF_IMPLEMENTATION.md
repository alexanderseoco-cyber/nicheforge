# Original Plan of Implementation

**Project:** NicheForge — Rank & Rent Niche Intelligence Engine  
**Phase:** Phase 1A — Durable Mock-Provider Validation Core  
**Status:** Approved; pre-implementation inspection authorized  
**Authority:** `PROJECT.md` and `docs/PROJECT_BLUEPRINT.md`

## Checkpoint status

- **Checkpoint A — Foundation:** Complete pending user review; Git baseline is intentionally deferred by explicit user instruction.
- **Checkpoint B — Evidence:** Complete pending user review.
- **Checkpoint C — Runs:** Complete pending user review.
- **Checkpoint D — Pipeline:** Complete pending user review.
- **Checkpoint E — Recalculation/Ledger:** Complete and user-approved.
- **Checkpoint F — Imports/Exports/Operational Intake:** Active; CSV-first import/export work and contained timestamp modernization are now authorized. Checkpoint F scope is governed by the approved blueprint additions and remains separate from the validated funnel.
- **Checkpoint F — Imports/Exports/Operational Intake:** Complete pending user approval; canonical imports, provider-specific evidence, provenance, exports, provider separation, incremental CSV safeguards, and file-backed acceptance are validated. No later checkpoint has started.
- **Checkpoint F — Import/Export:** Not started.
- **Checkpoint G — Acceptance:** Not started.

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

## Current Reconciliation — Checkpoint F Approved and Closed

Checkpoints A–F are complete and approved. The stale historical checkpoint bullets near the top of this document are superseded by this reconciliation record; no later checkpoint is authorized yet. See `docs/NEXT_PHASE_READINESS_REPORT.md` for the authoritative next-phase review.
