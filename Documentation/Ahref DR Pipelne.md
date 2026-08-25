# Ahrefs DR Proxy Pipeline

## Approval state

Approved implementation scope. This document records the plan before execution.
No live Ahrefs, Moz, or additional DataForSEO request is authorized during the implementation pass.

## Governing architecture

The existing Moz DA pipeline remains canonical and protected. Ahrefs Domain Rating (DR) is a separate, additive high-recall proxy pipeline and must never be stored or labelled as Moz DA.

Shared upstream flow:

`candidate -> population -> trusted SV -> SERP`

Authority branches:

`SERP -> Moz DA`

`SERP -> Ahrefs DR proxy -> strong/review/rejected shortlist -> manual Moz validation`

Existing CSV import, population, SV, SERP, cache, Run/RunCandidate, ProviderCall, recalculation, restart/resume, freshness, lineage, historical snapshots, and user-selected candidate scope remain backward-compatible.

## Implementation scope

1. Verify the current official Ahrefs endpoint, authentication, response mapping, rate limits, cost/API-unit behavior, and attribution requirements before implementing the live adapter. Record verified facts in project documentation.
2. Add an isolated Ahrefs provider identity: `provider=ahrefs`, `metric=domain_rating`, `pipeline=proxy_authority`.
3. Add separate Ahrefs DR evidence, cache, ProviderCall metadata, and provenance. Reuse normalized root-domain cache behavior where compatible.
4. Support fresh-cache reuse, stale detection, force refresh, deterministic batching, duplicate-domain deduplication, and auditable cache hits.
5. Add explicit classifications: `PROXY_STRONG_CANDIDATE`, `PROXY_REVIEW`, `PROXY_REJECTED_HIGH_CONFIDENCE`, and `PROXY_DATA_INCOMPLETE`.
6. Persist `RESULT`, `REASON`, `EVIDENCE`, `UNCERTAINTY`, `RECOMMENDED ACTION`, and `WHY NOT REJECTED` when applicable.
7. Add explicit `UNCALIBRATED_HIGH_RECALL` bootstrap mode. Do not invent a DR-to-DA conversion or claim Moz equivalence.
8. Add immutable calibration storage for Ahrefs DR and manually observed Moz DA pairs, including calibration versions and later recall/precision diagnostics.
9. Add canonical manual Moz observation entry and CSV import paths with `manual_moz` provenance, without overwriting Ahrefs evidence or creating `moz_api` evidence.
10. Snapshot proxy settings independently from Moz settings, including metric, calibration state/version, thresholds, uncertainty policy, freshness, evaluation mode, candidate scope, and policy version.
11. Preserve flexible processing: one, selected, first N, all, or larger imports. Internal batches must never impose a fixed candidate limit.
12. Reuse persisted SERP evidence only. Do not issue new DataForSEO, Moz, SV, Sandbox, or Production requests.
13. Implement adaptive/full proxy evaluation with explicit unchecked positions and false-negative-safe review routing.
14. Add candidate and batch reporting for targets, cache/network counts, classifications, manual Moz queue size, workload reduction, and calibration state.
15. Add mocked tests for provider mapping, credential redaction, identity isolation, cache behavior, batching, CSV compatibility, trusted SV preservation, persistence, ProviderCalls, restart/resume, recalculation, immutable Runs, all classifications, incomplete evidence, false-negative safety, manual Moz evidence, calibration, explanations, and arbitrary candidate counts.
16. Update project status and implementation documentation after actual validation.

## Non-negotiable safety boundaries

- Do not modify or reinterpret the existing Moz DA pipeline.
- Do not label Ahrefs DR as DA or use Moz PASS/IDEAL semantics for proxy-only results.
- Do not hard-code a candidate count such as 1,000.
- Do not fabricate population, SV, DR, or Moz DA values.
- Do not request or configure an Ahrefs API key during implementation.
- Do not make live Ahrefs, Moz, or additional DataForSEO requests.
- Do not commit automatically; leave validated changes available for review.

## Definition of done

The implementation pass is complete only after the independent proxy pipeline, evidence/cache, explanations, calibration/manual-Moz paths, flexible candidate processing, restart/recalculation behavior, documentation, and complete mocked regression suite are validated. Compilation, full tests, and `git diff --check` must pass, with confirmation that zero live provider calls occurred.
