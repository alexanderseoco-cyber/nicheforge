# NicheForge Task Completion Status

**Current phase:** Provider Readiness & Live Integration Boundary
**Status:** Provider Readiness complete; live provider activation intentionally deferred pending verified contracts, credentials, and explicit approval
**Last updated:** 2026-08-11

## Workflow rule

Every new change, completed task, milestone, or blocked task must update this status file. The update must record:

- task or milestone completed;
- files changed;
- validation actually executed;
- remaining work or blockers;
- corresponding section of `docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md` reconciled.

The implementation plan and this status file must remain synchronized. A phase may not be marked implemented until its required work and validation are complete.

## Latest update

- Reconciled the stale status header with the completed Checkpoints Aâ€“F and Provider Readiness history below.
- No live paid provider execution is authorized. Migration head: `d2a1f0c4e7b9`.
- Latest recorded validation: project-local Python 3.12.10; full suite `60 passed, 1223 warnings`; compilation and `git diff --check` passed. A later historical entry reports `61 passed, 1290 warnings` for additional recalculation-mode coverage.
- Remaining work is provider-contract verification before live calls, especially Moz authentication, metrics, KD, quotas, batching, rate limits, and billing.
- Reconciled plan reference: `docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md`, Provider Readiness & Live Integration Boundary.

- Recorded the verified Python 3.12 runtime in `PROJECT.md`.
- Authoritative executable: `D:\Python312\python.exe`.
- Verified version: Python 3.12.10.
- No implementation or migration work was performed.

## Checkpoint A update

- Established project-local `.venv` using `D:\Python312\python.exe` and Python 3.12.10.
- Installed backend dependencies into `.venv`; pip cache is under `.pip-cache`.
- Added `.gitignore`; Git initialization was intentionally skipped per user instruction.
- Added Alembic configuration and environment scaffolding.
- Added canonical statuses and reason codes.
- Added deterministic logical-candidate identity utilities using canonical identity plus SHA-256 key.
- Added initial `candidate_entities` SQLAlchemy model.
- Alembic autogeneration connected to root-local SQLite and detected the schema, but migration-file output was blocked by write permissions under `backend/alembic/versions`.
- Existing gate tests reached `4 passed`, but the pytest process timed out before clean completion; this is not recorded as a successful test-suite run.
- Checkpoint B has not started.

## Checkpoint A remediation

- Diagnosed Alembic write failure: the directory existed, had normal attributes and Modify ACLs, and a temporary write succeeded; the sandboxed Alembic process alone was denied when creating its generated migration. Running the unchanged Alembic command with approved elevation allowed Alembic itself to generate the migration.
- Corrected the Alembic template defect exposed during upgrade by adding the missing `sqlalchemy as sa` import.
- Generated migration `903990425cdf_initial_foundation_schema.py` through Alembic.
- Verified `alembic history`, empty-database upgrade, `alembic current`, and application startup against the migrated SQLite database.
- Diagnosed pytest non-termination with faulthandler: pytest hung in `_pytest.cacheprovider` while creating a temporary directory during session finish, not in application threads, SQLAlchemy, providers, or FastAPI lifecycle code.
- Configured pytest to disable the incompatible cache provider in this sandbox; this preserves test execution while avoiding the environment-level `tempfile.mkdtemp` hang.
- Added focused foundation tests for identity determinism, identity dimensions, canonical enums, model creation, and identity uniqueness behavior.
- The full Checkpoint A suite now exits normally with `8 passed`.
- Git remains intentionally uninitialized because the user explicitly requested that Git repository creation be ignored for now.

## Checkpoint B update

- Added append-only typed evidence models for population, search volume, authority, and extended SERP snapshots/results.
- Added provenance fields for provider, source kind, raw payload, request metadata, retrieval time, and freshness time.
- Added typed operational cache using `evidence_type` plus `evidence_id`; no ambiguous polymorphic database foreign key was introduced.
- Added centralized deterministic provider cache-key construction and per-evidence freshness evaluation.
- Added provider-call ledger with stage, operation, request key, outcome, cache hit, source kind, units, cost, currency, and error fields.
- Added import-batch provenance foundation for CSV/manual sources.
- Generated Alembic revision `a97fe719ed01_add_evidence_cache_provenance_and_.py` through Alembic.
- Corrected the SQLite migration to use batch mode for existing SERP table constraints.
- Verified empty-database upgrade through Checkpoint B head, `alembic current`, `alembic history`, and application startup.
- Added focused evidence, cache, freshness, provenance, provider-call, cost, and authority-scope tests.
- Final test result: `13 passed, 16 warnings in 2.24s`.
- Checkpoint C has not started.

## Checkpoint C update

- Added immutable historical `Run` model with typed primary-gate fields and canonical configuration/provider/freshness snapshots.
- Added `ProjectCandidate` membership model separate from global `CandidateEntity` identity.
- Added `RunCandidate` participation model with pinned population, search-volume, and SERP evidence IDs plus DA audit fields.
- Added append-only `CandidateEvent` history model.
- Added `RunCandidateAuthorityEvidence` lineage from run candidate to exact SERP result row and authority evidence version, including DA value used and weak-count flag.
- Linked `ProviderCall` to `Run` and `RunCandidate` while preserving cache/import/mock distinctions.
- Added uniqueness constraints and indexes for project membership, run participation, event lookup, and exact SERP-authority lineage.
- Generated Alembic revision `2aa370e8bd79_add_immutable_runs_events_and_evidence_.py` on top of `a97fe719ed01`.
- Corrected the SQLite migration to use batch mode for provider-call foreign keys.
- Verified Checkpoint B → C upgrade, `alembic current`, `alembic history`, and application startup.
- Added focused run, event, evidence-pinning, lineage, provider-linkage, and DA-boundary tests.
- Final test result: `17 passed, 61 warnings in 2.43s`.
- Checkpoint D has not started.

## Checkpoint D update

- Added synchronous `execute_run` orchestration service outside API route handlers.
- Implemented staged population → SV → SERP → authority → DA primary validation.
- Added strict fail-fast behavior for population and SV rejection, SERP insufficiency, and incomplete authority evidence.
- Pinned exact population, SV, and SERP evidence to `RunCandidate`.
- Created exact SERP-result → authority-evidence lineage for every evaluated organic result.
- Implemented conservative authority completeness policy: the primary DA gate runs only when configured organic depth is present and every evaluated result has usable DA; otherwise the candidate is retryable/incomplete and cannot pass.
- Implemented strict `DA < threshold` calculation with missing DA excluded from weak count.
- Added provider/cache handling, provider-call records, mock-provider execution, run counters, event generation, and current ProjectCandidate summary projection.
- Added canonical `/projects/{project_id}/runs`, `/runs/{run_id}`, and `/runs/{run_id}/execute` API endpoints.
- Added idempotent completed-run re-execution behavior.
- Generated migration `ba2281e098cb_add_run_counters.py`.
- Verified the migration and application startup at head.
- Added deterministic pipeline and fail-fast tests.
- Final test result: `21 passed, 217 warnings in 5.43s`.
- Checkpoint E has not started.

## Checkpoint E update

- Added recalculation run metadata: `Run.run_type` and nullable `Run.parent_run_id`.
- Added centralized search-volume, SERP, and authority evidence compatibility helpers.
- Added recalculation service that creates a new historical run and preserves the parent run.
- Added recalculation preview with affected-candidate, reusable-SV, fresh-SV, estimated-call, and estimated-cost counts.
- Added batch-capable recalculation and ledger/history query services with pagination and status filtering.
- Added API endpoints for recalculation preview, recalculation execution, project ledger, and project-candidate history.
- Preserved old runs and run-candidate outcomes during recalculation.
- Verified lower SV threshold re-admission from stored SV evidence without a second SV provider call.
- Fixed the project-local `tldextract` cache path to prevent sandbox writes into site-packages during recalculation/pipeline execution.
- Generated migration `6f66991da474_add_recalculation_run_metadata.py`.
- Verified migration head and application startup.
- Final test result: `23 passed, 293 warnings in 3.44s`.
- Checkpoint F has not started.

## Checkpoint E remediation update

- Expanded preview across population, SV, SERP, authority, DA recomputation, reusable evidence, fresh-stage estimates, provider-call estimates, and cost estimates.
- Added fast-path recalculation from exact pinned population/SV/SERP/authority evidence for compatible completed candidates.
- DA threshold and required weak-site changes now create new RunCandidates while preserving old outcomes and exact authority lineage.
- Expanded ledger rows with current state, latest SV/provider/timestamp, DA summary, historical run count, and pagination/status filtering.
- Expanded candidate history into human-readable run/threshold/result/authority-lineage details.
- Preserved current summary when a new incomplete/error run is not a terminal automatic result.
- Added project-local tldextract cache handling to prevent site-package cache writes.
- Full suite remains `23 passed, 293 warnings`.
- Remaining E limitations are documented for review: advanced ledger filters beyond status, explicit stale-policy modes, and comprehensive compatibility/restart test coverage still need further hardening before Checkpoint F.

## Checkpoint E hardening update

- Added first-class `FreshnessPolicy`: `REUSE_FRESH_ONLY`, `ALLOW_STALE_WITH_WARNING`, and `FORCE_REFRESH`.
- Snapshotted freshness policy on `Run` and added centralized policy evaluation.
- Added explicit compatibility tests for SV, SERP, and authority request dimensions.
- Added migration `9d6445dbc7ae_add_freshness_policy_mode.py` and verified head.
- Full suite now reports `25 passed, 293 warnings in 1.78s`.
- Remaining requested E hardening—full stage-integrated stale/force-refresh behavior, comprehensive ledger filters, organic-depth execution tests, and persistent restart acceptance—still requires implementation before E can be approved.

## KD configuration update

- Added configurable keyword difficulty support with Moz as the default provider, preferred threshold `<15`, strict operator `<`, and default `PRIORITY` mode.
- Added optional `HARD_GATE` semantics and canonical `KD_ABOVE_THRESHOLD` reason code.
- Added append-only `KeywordDifficultyEvidence` separate from SV and authority evidence.
- Extended keyword provider results so one provider response may produce SV and KD evidence without duplicate provider-call accounting when actually supported.
- Added KD fields to Run and RunCandidate for historical threshold/value/status pinning.
- Added migration `5c45b58975e9_add_keyword_difficulty_evidence_and_.py`.
- Updated `PROJECT.md` with Moz KD defaults and the rule not to assume shared Moz endpoint or zero incremental billing until verified.
- Full suite: `27 passed, 309 warnings in 4.76s`.

## Checkpoint E KD integration update

- Fixed KD derivation on search-volume cache hits: existing keyword-difficulty evidence is now reused independently of the in-process provider result.
- Fixed recalculation persistence ordering so newly created RunCandidates receive their immutable authority-lineage rows safely.
- Added an integrated recalculation test proving KD threshold changes reuse the exact evidence ID and create zero additional provider calls while leaving the parent run unchanged.
- Full suite: `32 passed, 392 warnings in 1.99s`.
- Checkpoint E remains in progress pending the previously identified full stage-integrated freshness behavior, comprehensive ledger filters, organic-depth execution coverage, and restart-persistence acceptance tests.

## Checkpoint E workflow-order correction

- Updated the business workflow to `Population -> SV -> DA -> deeper SERP analysis -> KD -> Result/History`.
- Documented the technical distinction between SERP acquisition (required to obtain organic competitors for DA) and deeper SERP analysis.
- Moved KD evaluation in the executable pipeline until after the DA primary evaluation.
- `HARD_GATE` KD now rejects only DA-qualified candidates; KD cannot override a failed DA primary gate.
- Preserved KD evidence reuse, append-only history, provider abstraction, and threshold recalculation semantics.
- Full suite: `32 passed, 386 warnings in 1.99s`.

## Checkpoint E hardening continuation

- Added composable ledger filter parameters for category hierarchy, state, population, SV, KD provider/range/classification, low-DA count, primary result, and reason code at the service/API boundary.
- Preserved the approved workflow order: SERP acquisition precedes DA evaluation; KD evaluation follows DA.
- Full suite after the change: `32 passed, 386 warnings in 2.57s`.
- Checkpoint E is still open: execution-level freshness policies, full DA-centric golden coverage, organic-depth compatibility, current-summary edge cases, preview mutation acceptance, file-backed restart acceptance, and the final multi-candidate acceptance scenario remain to be completed.

## Checkpoint E freshness continuation

- Integrated run freshness-policy lookup for search-volume and keyword-difficulty cache reuse.
- `REUSE_FRESH_ONLY` refreshes stale evidence; `ALLOW_STALE_WITH_WARNING` reuses stale evidence and appends an explicit `STALE_EVIDENCE_REUSED` event; `FORCE_REFRESH` bypasses cached evidence.
- Preserved immutable evidence and actual provider-call accounting.
- Full suite: `32 passed, 386 warnings in 5.54s`.
- SERP/authority freshness execution, organic-depth compatibility, summary protection, preview counts, restart acceptance, and final integrated scenario remain open.

## Checkpoint E SERP freshness continuation

- Added policy-aware SERP snapshot cache lookup with request-dimension cache keys.
- Fresh compatible snapshots reuse; stale snapshots follow the run policy; forced/deeper requests acquire a new immutable snapshot.
- Stored organic rows are reused only when their stored depth satisfies the requested depth; rows are truncated to the requested depth for evaluation and missing positions are never synthesized.
- SERP cache reuse/fetch calls and stale-warning events are recorded.
- Full suite: `32 passed, 394 warnings in 1.99s`.
- Authority freshness execution, current-summary protection, preview mutation proof, restart acceptance, and final integrated scenario remain open.

## Checkpoint E authority freshness continuation

- Added provider/URL/domain/target-type scoped authority cache keys.
- Authority evidence now follows the run freshness policy: fresh reuse, stale refresh, stale reuse with warning, or forced refresh.
- New authority evidence is append-only; historical RunCandidates continue pointing to their original evidence IDs.
- Authority provider calls and cache hits are now recorded per target, with no call for compatible reused evidence.
- Full suite: `32 passed, 474 warnings in 1.97s`.
- Current-summary protection, preview mutation proof, restart acceptance, DA-only golden tests, and final integrated scenario remain open.

## Checkpoint E closure-test continuation

- Added DA-only recalculation golden coverage: required weak-site count changes and DA threshold changes reuse the exact SERP snapshot and authority lineage with zero additional provider calls; the parent Run remains unchanged.
- Added full preview mutation-count proof across Runs, RunCandidates, events, all evidence tables, snapshots, authority evidence, and ProviderCalls.
- Added current-summary protection coverage: retryable attempts do not replace a valid PASS; a completed PRIMARY_REJECTED recalculation does replace it.
- Full suite: `35 passed, 781 warnings in 2.14s`.
- File-backed restart acceptance and the final multi-candidate integrated scenario remain open; Checkpoint E is not yet complete.

## Checkpoint E restart acceptance

- Added file-backed SQLite restart coverage under the project-local test temporary data path.
- Reopened a fresh engine/session and reconstructed Run A, recalculation Run B, parent linkage, RunCandidates, evidence pins including KD, events, ProviderCalls, current summary, ledger, and history.
- Restart test passed independently: `1 passed, 95 warnings in 1.59s`.
- Full suite now: `36 passed, 876 warnings in 2.84s`.
- The final multi-candidate integrated Rank & Rent acceptance scenario remains the sole required closure item; Checkpoint E remains open.

## Checkpoint E final integrated acceptance — COMPLETE

- Added an automated seven-candidate deterministic Rank & Rent acceptance scenario covering population rejection, SV rejection, DA rejection despite excellent KD, DA PASS with KD IDEAL, DA PASS with KD ABOVE_PREFERRED, DA-first KD HARD_GATE rejection, and incomplete/retryable SERP evidence.
- Recalculation coverage changes SV, DA weak-site count, and KD thresholds while preserving Run A and reusing compatible evidence in Run B.
- Acceptance assertions verify evidence IDs, parent linkage, current ledger/history reconstruction, cache hits, and no new successful provider calls for reusable evidence.
- Full suite: `37 passed, 1338 warnings in 3.19s`.
- Migration head: `5c45b58975e9`.
- Checkpoint E is complete and Checkpoint F remains blocked pending user approval.

## Checkpoint E approval / Checkpoint F opened

- Checkpoint E approval recorded from user review.
- Checkpoint F is now active: Imports, Exports, and Operational Data Intake.
- Preserved the canonical workflow: Population -> SV -> SERP acquisition -> DA primary gate -> deeper SERP analysis -> KD -> Result/History.
- Checkpoint F scope includes CSV-first intake/export, provider-specific provenance, import reports, duplicate/conflict handling, historical exports, security protections, and contained timestamp modernization.
- Checkpoint F does not include secondary scoring, monetization, Chrome extension expansion, live provider integration, queues, authentication, or frontend redesign.

## Checkpoint F timestamp modernization

- Replaced application-service `datetime.utcnow()` calls with a contained UTC helper that returns naive UTC values for compatibility with the existing database DateTime columns.
- Preserved timestamp semantics and database compatibility without introducing a migration.
- Full suite after modernization: `37 passed, 934 warnings in 3.41s`.
- Remaining warnings are concentrated in model defaults and tests; import/export implementation has not yet started.

## Checkpoint F import framework continuation

- Added canonical CSV import service using the existing ImportBatch, CandidateEntity, ProjectCandidate, SearchVolumeEvidence, and KeywordDifficultyEvidence models.
- Added niche CSV/plain-text intake with raw-row provenance.
- Added localized candidate resolution with unresolved-row retention and no fabricated city matches.
- Added Keywords Everywhere and Ahrefs keyword-export ingestion with distinct provider/source identities.
- Added imported SV/KD evidence through canonical append-only evidence models.
- Added file-hash duplicate detection and import report counts.
- Added API routes for niche, Keywords Everywhere, and Ahrefs imports.
- Added focused import tests; full suite: `39 passed, 942 warnings in 3.16s`.
- City/population, Moz, manual evidence, exports, formula-injection protection, and large-file hardening remain in Checkpoint F.

## Checkpoint F city/export continuation

- Added city/population CSV import with validation for names, state codes, population, vintage, Census ID, duplicate vintage rows, newer vintages, and conflicting observations.
- Added city import persistence and conflict tests.
- Added pinned Run CSV export using RunCandidate evidence references for population, SV, KD, DA summary, thresholds, status, and reason codes.
- Added historical export regression proving a later SV observation does not leak into an older Run export.
- Added `/projects/{project_id}/imports/cities` and `/runs/{run_id}/export` routes.
- Full suite: `41 passed, 998 warnings in 3.25s`.
- Remaining F work: explicit population-evidence import linkage, Moz/manual evidence, project/candidate-history exports, formula-injection and large-file hardening, Ahrefs format detection, and imported-evidence execution integration.

## Checkpoint F provenance continuation

- Localized imported candidates now materialize imported city observations into canonical PopulationEvidence and the normal population cache pointer, preserving ImportBatch provenance.
- Added Moz CSV ingestion with scoped `moz_csv` KD, URL/domain authority evidence, PA, DA, spam, linking-domain, and backlink mappings; unknown columns remain in raw provenance.
- Added controlled manual keyword SV/KD evidence with `source_kind=manual` and note provenance.
- Added Moz and manual API routes.
- Added tests for population-vintage handling, Moz scope/provenance, and manual evidence.
- Full suite: `42 passed, 1006 warnings in 3.63s`.
- Remaining F work: project/candidate-history exports, formula-injection and large-file hardening, Ahrefs format detection, imported-evidence execution integration, and import-batch detail/error APIs.

## Checkpoint F export/reporting continuation

- Added current project-ledger CSV export and candidate-history CSV export using canonical ledger/history services.
- Added spreadsheet formula-cell protection for exported text fields.
- Added import upload-size and row-count guardrails.
- Added Ahrefs format detection metadata for keyword-level versus repeated-keyword SERP-expanded files.
- Added project export and candidate-history export API routes.
- Full suite: `42 passed, 1006 warnings in 3.37s`.
- Remaining F work: detailed imported-evidence execution reuse, formal Ahrefs repeated-row tests, import-batch detail/error APIs, stronger streaming/field/encoding validation, and final export coverage.

## Checkpoint F integration/API continuation

- Connected imported KE SV, Moz KD, and Moz authority observations to canonical provider-cache keys for validator reuse while preserving source identity.
- Added import-batch detail and error inspection APIs.
- Added project and candidate-history export services/routes with current-vs-historical semantics.
- Added Ahrefs repeated-keyword format metadata and row-count/upload safeguards.
- Full suite: `42 passed, 1008 warnings in 3.41s`.
- Remaining F work: end-to-end imported-evidence pipeline tests, formal repeated-row deduplication tests, stronger streamed/field/encoding validation, and final import-driven acceptance coverage.

## Checkpoint F closure-test continuation

- Added actual normal-pipeline integration coverage proving imported KE SV and Moz KD are consumed without a new SV provider success call or KD fetch.
- Added Ahrefs SERP-expanded repeated-row detection and logical deduplication while retaining raw import/report provenance.
- Added UTF-8, malformed CSV, header, field-length, upload-size, and row-count safeguards.
- Added project/candidate-history export routes and import-batch detail/error routes.
- Full suite: `44 passed, 1072 warnings in 3.61s`.
- Remaining F work: full imported Moz authority reuse test, Ahrefs-vs-Moz provider separation test, streamed parsing refinement, and the final import-driven restart/export acceptance scenario.

## Checkpoint F authority/provider closure continuation

- Added normal-pipeline Moz authority reuse coverage with exact URL/domain scope; imported DA drives the primary gate without an authority-provider call.
- Added imported Moz KD cache compatibility while preserving provider-specific source identity.
- Full suite: `45 passed, 1097 warnings in 4.26s`.
- Remaining F work: explicit Ahrefs-vs-Moz integration separation, streamed parser refinement, and the final file-backed import/recalculate/export/restart acceptance scenario.

## Checkpoint F completion — PENDING APPROVAL

- Added execution-path provider separation: Ahrefs KD is not consumed by Moz-configured Runs.
- Converted keyword CSV ingestion to incremental `csv.DictReader` processing with upload, row, field, encoding, header, delimiter, and malformed-row safeguards.
- Added late-parse error reporting with accepted/rejected counts preserved.
- Added final file-backed import → Run A → recalculation Run B → project/Run/history export → close/reopen acceptance coverage.
- Verified import batches, evidence provenance, provider identities, parent linkage, exports, and historical reconstruction after restart.
- Full suite: `47 passed, 1217 warnings in 4.55s`.
- Migration head: `5c45b58975e9`.
- Checkpoint F implementation is complete pending user approval; no later checkpoint has started.

## Checkpoint F provider-separation continuation

- Added execution-path KD provider compatibility checks.
- Added normal-pipeline proof that Ahrefs KD is not consumed by a Moz-configured Run.
- Preserved Moz CSV and Ahrefs CSV evidence as separate immutable observations.
- Full suite: `46 passed, 1149 warnings in 4.06s`.
- File-backed import/recalculate/export/restart acceptance and streamed incremental parser work remain open.

## Checkpoint F approval and readiness review

- Checkpoint F approved and closed by user.
- Final accepted baseline: `47 passed, 1217 warnings in 4.55s`; migration head `5c45b58975e9`.
- Added `docs/NEXT_PHASE_READINESS_REPORT.md` reconciling Blueprint completion, partial areas, untouched phases, dependencies, technical debt, documentation consistency, and recommended next checkpoint.
- No next checkpoint has started; recommended next phase is provider-readiness/integration-boundary review.
- Created `docs/API_KEYS_AND_PROVIDER_ACCESS_RULES.md` as the dedicated credential, provider-mode, cost, paid-call, and DA/adaptive-authority rules artifact.
- Provider Readiness & Live Integration Boundary is now the active planning checkpoint; no live paid calls are enabled.
- Recorded API-key/provider access rules in `docs/API_KEYS_AND_PROVIDER_ACCESS_RULES.md`.
- Recorded approved DA semantics: minimum weak domains `4` = PASS, ideal weak domains `5+` = IDEAL, configurable and Run-snapshotted; adaptive authority mode is planned as the bulk default.
- Updated `PROJECT.md` and `docs/PROJECT_BLUEPRINT.md` only for this approved architectural change. Existing implementation fields still require the Provider Readiness checkpoint’s migrations and tests before live activation.
- No credentials were added, no live provider calls were made, and no production paid mode was enabled.

## Provider Readiness contained implementation

- Added deterministic adaptive/full authority evaluation service with 4=PASS, 5+=IDEAL, mathematical failure, unchecked-position preservation, and cached/fetched target accounting fields.
- Added DataForSEO runtime mode/budget guard boundary: SANDBOX default, TRIAL approval/ceiling checks, PRODUCTION disabled by default.
- Added provider-readiness tests; full suite: `52 passed, 1217 warnings`.
- Official DataForSEO research recorded Sandbox as free/dummy-data and documented Standard/Live/depth/rate-limit facts. Moz endpoint, quota, KD, batching, and billing details remain UNVERIFIED.
- No credentials requested or inserted; no live paid API call made.
- Repository initialized and pushed to the supplied GitHub remote in commit `40d75a1`.
### Provider Readiness — persisted adaptive authority boundary

- Added persisted Run configuration for minimum/ideal weak domains, authority evaluation mode, and adaptive batch size.
- Added RunCandidate audit fields for evaluated, cached, fetched, unchecked, confirmed-weak, classification, and threshold values.
- Wired the canonical evaluator into the persisted pipeline while preserving legacy `required_low_da_count` compatibility.
- Added migration `d2a1f0c4e7b9` and verified the migration head and restart-compatible schema upgrade.
- Verification: `52 passed, 1217 warnings`.
- Still pending in this checkpoint: official DataForSEO Sandbox adapter/contract tests, adaptive cost-preview integration, and expanded persisted recalculation tests for all new fields. Moz remains research-only and unverified; no credentials or paid calls used.

### Provider Readiness — Sandbox boundary and preview

- Added a network-independent DataForSEO Sandbox SERP response mapper with explicit `dataforseo_sandbox` provenance and no implicit transport/fallback.
- Added Sandbox contract tests for organic filtering, requested depth, provenance, zero-cost mode, and paid-path rejection.
- Added adaptive authority/cost preview fields with `KNOWN`, `UPPER_BOUND`, and `ESTIMATE` confidence labels.
- Added the research-only [Moz provider contract status](../docs/MOZ_PROVIDER_CONTRACT_STATUS.md); unresolved contract and billing details remain `UNVERIFIED`.
- Verification: `54 passed, 1217 warnings`.

### Provider Readiness — explicit adaptive stopping policy

- Added persisted `adaptive_seek_ideal` configuration and RunCandidate audit snapshot.
- Preview now reports `seek_ideal` alongside adaptive mode, thresholds, batch size, and confidence-labelled target estimates.
- Default behavior is to continue after PASS when IDEAL remains possible; ultra-low-cost PASS-only behavior is configurable.
- Verification remains `54 passed, 1217 warnings`.

### Provider Readiness — final deterministic comparison coverage

- Added an opt-in-only Sandbox smoke transport controlled by `NICHEFORGE_ENABLE_DATAFORSEO_SANDBOX_SMOKE=1`; default tests remain offline and deterministic.
- Added the 100-candidate ADAPTIVE-versus-FULL deterministic comparison. It proves target reduction, IDEAL/PASS/rejection classifications, and truthful unchecked counts.
- Added smoke-boundary and 100-candidate acceptance tests.
- Verification: `56 passed, 1217 warnings`.

### Provider Readiness — Trial budget guard coverage

- Added explicit remaining Trial budget configuration with exact-boundary enforcement.
- Added tests for below-budget, exactly-at-budget, above-budget, missing approval/credentials, disabled provider, and historical configuration immutability.
- Verification: `58 passed, 1217 warnings`.

### Provider Readiness — persisted adaptive matrix

- Added file-backed restart coverage for parent/recalculation Run configuration and RunCandidate adaptive audit fields.
- Added deterministic threshold, mode, and seek-ideal matrix assertions.
- Verified historical parent and recalculation records remain independently persisted.
- Verification: `60 passed, 1223 warnings`.

### Trial Readiness — complete

- Wired exact DataForSEO location resolution into Trial SERP execution, including cached location reuse and provider `location_code` submission.
- Trial requests route through the main DataForSEO host, remain isolated from Sandbox, and cannot fall back across modes.
- Trial responses persist through canonical `SerpSnapshot` and `SerpResultRow` records with explicit `dataforseo_trial` provenance.
- Trial execution records one linked `ProviderCall` with provider, `TRIAL` mode, operation, Run/RunCandidate linkage, timestamps, estimated cost, returned actual cost, or null actual cost when unavailable.
- Trial Run pricing and budget context remains in the immutable Run configuration snapshot; later configuration changes do not mutate historical context.
- Added mocked boundary coverage for exact resolution, cache reuse, Trial host routing, canonical evidence, provenance, ProviderCall linkage/costs, historical snapshots, Sandbox isolation, Production disabling, and no cross-mode fallback.
- Validation: targeted Trial/provider tests `14 passed`; full mock-provider suite `68 passed, 1087 warnings`; Python compilation and `git diff --check` passed. No real Trial or Production request was made.
- Reconciled plan reference: Provider Readiness & Live Integration Boundary in `docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md`.

### Ahrefs DR Proxy Pipeline - implementation complete

- Verified the official Ahrefs free Domain Rating contract and recorded it in `docs/AHREFS_DR_PROXY_STATUS.md`.
- Added isolated Ahrefs DR provider transport, configuration, proxy evidence, cache identity, ProviderCall accounting, Run/RunCandidate proxy snapshots, high-recall classifications, explanation fields, and uncalibrated bootstrap state.
- Added immutable paired calibration storage and manual Moz single-entry/CSV observation paths with `manual_moz` provenance. Moz DA evidence and semantics remain separate.
- Added migration `a8ahrefsproxy`; fresh-chain migration validation passed without leaving a test database. The existing `backend/nicheforge.db` was restored to its prior migration state after validation and was not used for final migration testing.
- Added mocked Ahrefs contract, identity, false-negative safety, classification, and manual-provenance coverage. Existing Moz/CSV/SV/SERP behavior remained green.
- Validation: targeted tests `13 passed`; full mock suite `71 passed, 1089 warnings`; compilation and `git diff --check` passed. No live Ahrefs, Moz, or additional DataForSEO request was made.
- Remaining boundary: live Ahrefs smoke testing requires separate API-key configuration and explicit authorization.

### Ahrefs live execution guard - complete

- Enforced `AHREFS_PROXY_ENABLED` and explicit `AHREFS_LIVE_APPROVED` checks before Ahrefs transport construction.
- Missing credentials, disabled proxy, and missing approval now fail before network execution; defaults remain false.
- Added mocked disabled, missing-key, unapproved, and approved-boundary tests.
- No `.env` changes and no live Ahrefs, Moz, or DataForSEO requests were made.

### DataForSEO proxy backlink enrichment - implementation complete

- Verified and documented the official Bulk Pages Summary Live contract in `docs/DATAFORSEO_PROXY_FEATURE_STATUS.md`.
- Added separate DataForSEO backlink-feature provider, evidence model, cache identity, cost/API-status fields, and ProviderCall accounting. One response can populate Rank, backlinks, referring-domain, IP/subnet, nofollow, and spam-score features.
- Added independent calibration feature storage and inactive-by-default reject-audit Run configuration support. No DR-to-DA conversion was introduced.
- Added mocked contract, guard, multiple-feature mapping, cache deduplication, and provider-isolation coverage.
- No credentials were changed and no live Ahrefs, Moz, or DataForSEO request was made during this implementation pass.

### Ahrefs DR Proxy Pipeline - implementation approved, not started

- Recorded the approved additive Ahrefs DR high-recall proxy scope in `Ahref DR Pipelne.md`.
- Moz DA remains the protected canonical authority pipeline; Ahrefs DR will remain a separate provider, metric, evidence lineage, cache, classification, and calibration path.
- Candidate count remains user-controlled; existing CSV, population, trusted SV, SERP, cache, Run/RunCandidate, ProviderCall, recalculation, restart/resume, and historical snapshot behavior must remain intact.
- Implementation is authorized to proceed, but no Ahrefs API key has been requested and no live Ahrefs, Moz, or additional DataForSEO request has been made.
- Reconciled plan reference: additive authority-proxy implementation following the Provider Readiness & Live Integration Boundary.

### Provider Readiness - adaptive authority continuation refactor

- Recalculation execution now acquires unresolved authority targets in ordered adaptive batches, reuses compatible cached evidence, preserves SERP-to-authority lineage, records one ProviderCall per issued batch, and leaves post-stop positions unchecked.
- FULL mode continues to acquire the complete unresolved authority depth.
- Validation: Python compilation and `git diff --check` passed. Targeted pytest execution was unavailable because the project environment has no pytest installation.

### Provider Readiness COMPLETE - final closure

- Persisted authority semantics are DA < 10, 4 weak domains = PASS, and 5+ weak domains = IDEAL; thresholds and mode are Run-snapshotted.
- ADAPTIVE recalculation is cache-first and acquires only ordered unresolved targets in configured incremental batches. `adaptive_seek_ideal` governs continuation after PASS; batch size is persisted and auditable.
- FULL mode retains complete-depth authority acquisition. ProviderCall accounting records one call per issued authority batch; cache hits do not create provider calls.
- SERP-result to authority-evidence lineage remains append-only, with genuinely unchecked positions persisted. Parent Runs remain historical; restart reconstruction and retry/idempotency coverage passed.
- The 100-candidate deterministic ADAPTIVE-vs-FULL benchmark, Sandbox boundary, Trial guards, Production-disabled guard, and adaptive cost-preview coverage remain passing.
- DataForSEO Sandbox is network-independent and ready for opt-in smoke use. Trial requires explicit approval, credentials, and budget; Production remains disabled by default. No credentials or live/paid calls were used.
- Moz contract status remains PARTIALLY_VERIFIED/UNVERIFIED for unresolved endpoint, quota, batching, KD, and billing details; it is not enabled as a live dependency.
- Migration head: `d2a1f0c4e7b9`.
- Final validation: project `.venv` Python 3.12.10; targeted `12 passed, 372 warnings`; full suite `61 passed, 1083 warnings`; compilation and `git diff --check` passed.
- GitHub synchronization: origin is configured, but the validated implementation and status update are currently uncommitted locally and therefore not yet synchronized to GitHub.
- Remaining Provider Readiness blockers: none substantive. Live provider activation remains intentionally deferred pending verified provider contracts and explicit credentials/approval.

### Provider Readiness — actual recalculation mode coverage

- Added an actual `recalculate()` integration test covering ADAPTIVE → FULL, seek-ideal snapshot changes, batch-size snapshotting, SERP lineage reuse, and zero additional provider calls when complete evidence exists.
- Verification: `61 passed, 1290 warnings`.

### Provider Readiness — actual recalculation audit integration

- The real `recalculate()` path now snapshots adaptive mode, seek-ideal, thresholds, and audit counts on recalculated RunCandidates.
- Existing DA-only recalculation tests now verify reused lineage, zero additional ProviderCalls, historical Run immutability, and persisted audit fields.
- Verification: `60 passed, 1223 warnings`.

### Live Trial validation — complete

- The first real Trial diagnostic reached DataForSEO but returned HTTP 200/API `40501 Invalid Field: 'location_name'`; it cost `$0.00` and is preserved as an auditable invalid, non-reusable snapshot with a failed Trial ProviderCall.
- Corrected Trial requests to send only the provider-verified `location_code` when available; added exact provider-location cache support for `Salina,Kansas,United States` / `1017623` without embedding Salina-specific production business logic.
- The second controlled real Trial request for `pest control salina ks` succeeded with HTTP 200/API `20000 Ok`, requested depth 10, and 9 actual organic rows. No tenth row was fabricated.
- Successful Trial evidence persisted canonically with `dataforseo_trial` provenance, SERP Snapshot ID `340dc635-b1ff-4d8d-bc7d-692cfe3a0aca`, one successful linked ProviderCall `33c23bcd-45c0-4743-9c4a-802b4e175af9`, estimated cost `$0.002`, actual cost `$0.002`, and remaining configured budget `$0.008`.
- No SV, Moz, Sandbox, Production, or existing `backend/nicheforge.db` access occurred during the successful Trial request. The disposable validation database was `backend/nicheforge_trial.db`.
- Added regression coverage preventing application-level provider errors from becoming reusable SERP evidence or cache entries.
- Validation: targeted Trial/location/Sandbox tests `10 passed`; full mock-provider suite `68 passed, 1089 warnings`; no additional live request was made after the successful second request.
- Reconciled plan reference: Provider Readiness & Live Integration Boundary in `docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md`.
# DataForSEO backlink mapper repair

- Confirmed the live schema uses `tasks[0].result[0].items[].url`, not `item.target`.
- Added URL/root-domain mapping, null-preserving feature extraction, mapping status/error fields, and sanitized raw-response persistence.
- Added regression coverage for multi-target mapping, missing items, cost propagation, and cache/provider-call behavior.
- Reclassified the original five paid evidence rows as `unrecoverable_raw_missing` because their raw response was not persisted; original ProviderCall and `$0.02418` actual cost remain unchanged.
- No additional DataForSEO, Ahrefs, Moz, SERP, or SV requests were made.

### Keyword Metrics Engine plan — recorded

- Added `integration of Search Volume and Trend plan.md` as the governing plan for the standalone, provider-neutral search-volume and trend engine.
- Incorporated immutable evidence refreshes, provider-returned keyword identity, distinct zero/unknown/paid cost semantics, API-before-UI sequencing, optional Google Ads provider implementation, profile-specific SV thresholds, and reusable evidence across validation profiles.
- No implementation or provider request has started in this milestone.

### Keyword Metrics Engine Phase 1 — started

- Added provider-neutral `KeywordMetricQuery`, append-only `KeywordMetricEvidence`, and `KeywordMetricBatch` models.
- Added migration `backend/alembic/versions/c2_keyword_metrics_engine.py`; Alembic reports `c2keywordmetrics` as the current head.
- Extended keyword metric contracts with country/targeting, provider-returned keyword identity, competition index, bid fields, and explicit cost.
- Validation executed: foundation/evidence tests `9 passed`; diff check clean.
- Compilation was attempted but Python could not replace two locked project `__pycache__` files; no source compilation error was reported.
- No live Google Ads, DataForSEO, Moz, Ahrefs, or SV provider requests were made.

### Keyword Metrics Engine Phase 2 — provider boundary

- Added explicit keyword-metrics provider factory selection for mock, imported, Google Ads, and DataForSEO providers.
- Unknown providers now fail explicitly; no silent fallback is permitted.
- Added provider-boundary tests for unknown selection, disabled/unapproved Google guards, and zero-cost mock identity mapping.
- Batch orchestration and API contracts remain next; provider transport remains disabled.

### Keyword Metrics Engine Phase 2 — cache-aware batch contract

- Added cache-first batch orchestration with fresh-hit reuse, stale/missing batching, explicit unmapped results, and idempotent resume behavior.
- Added four regression tests covering provider-call suppression, selective batching, partial responses, and restart/resume deduplication.
- Provider transport remains disabled; no live requests were made.

### Keyword Metrics Engine Phase 2 — research API contracts

- Added thin preview, research, list, detail, and refresh API endpoints.
- Added request, preview, result, and research response schemas exposing provider, targeting, mapping status, metrics, batch status, and cost fields.
- Research routes delegate to the provider factory and batch orchestrator; validation handoff/export remain deferred.

### Keyword Metrics Engine Phase 2 — PASS

- Provider abstraction: PASS.
- Provider factory and no-silent-fallback behavior: PASS.
- Google pre-transport guards: PASS.
- Cache-aware orchestration, deduplication, and restart safety: PASS.
- Research API contracts: PASS.
- Added direct API tests for non-transporting preview, mock research, unknown provider rejection, unmapped serialization, and evidence retrieval.
- AST compilation: PASS.
- `git diff --check`: PASS.
- Live-provider isolation: PASS.

### Keyword Metrics Engine Phase 3 — started

- Next scope is configuration and safety-boundary formalization only; live Google transport remains disabled.

### Keyword Metrics Engine Phase 3 — safety boundary implemented

- Added explicit provider enablement, approval, credential, batch-size, request-rate, freshness, and budget guards.
- Added secret-safe error/log redaction.
- Google Ads factory selection now validates credential presence before transport.
- Added tests for missing credentials, budget/batch/rate rejection, and secret leakage prevention.
- No live provider requests were made; truthful ProviderCall persistence remains part of the batch persistence closure.

### Keyword Metrics Engine Phase 3 — PASS

- Provider enablement/approval, credentials, batch size, rate, freshness, budget, redaction, factory guards, and explicit pre-transport failures: PASS.
- Tests: 16 passed; AST compilation: PASS; `git diff --check`: PASS; live-provider isolation: PASS.

### Keyword Metrics Engine Phase 4 — started

- Added deterministic cache identity for normalized keyword, location name, structured geo target, language, country, provider, and metric version.
- Targeted and nationally embedded geographic queries are intentionally distinct identities.

### Keyword Metrics Engine Phase 4 — PASS

- Cache identity includes targeting context, provider, and metric version; targeted and embedded geographic queries cannot collide.
- Tests: 19 passed; AST compilation: PASS; `git diff --check`: PASS.

### Keyword Metrics Engine Phase 5 — started

- Extended batch orchestration with arbitrary-size input, provider-limit chunking, per-chunk request counts, aggregate cost, and resume-safe evidence reuse.
- Added targeting-mode identity support for future provider/network-scope changes.

### Keyword Metrics Engine Phase 5 — PASS

- Arbitrary input, provider chunking, per-chunk accounting, aggregate costs, unmapped preservation, restart safety, and targeting-aware identity: PASS.
- Tests: 20 passed; AST compilation: PASS; `git diff --check`: PASS.

### Keyword Metrics Engine Phase 6 — started

- Added neutral research-workspace filtering/sorting, stale-evidence selection, and export-row preparation.
- No population gate, SV rejection, or automatic validation handoff is applied by the workspace.

### Keyword Metrics Engine Phase 6 — core PASS / overall IN PROGRESS

- Core research/result processing: PASS.
- Single and bulk keyword request contracts, targeting/language fields, cache preview, stale selection, history visibility, filtering/sorting, and export-row preparation are available.
- Full user-facing workspace closure remains deferred: CSV upload UI, keyword×city generation UI, monthly-history presentation, and actual CSV/PDF export are not yet claimed complete.
- These remaining presentation/export operations are explicitly deferred to the planned UI/integration phase; no population gate, universal SV threshold, automatic rejection, or validation handoff will be introduced.

### Keyword Metrics Engine Phase 7 — started

- Added explicit subset-only `send-to-validation` handoff records referencing immutable evidence IDs.
- Handoff preserves submitted/provider keyword identity, targeting, provider, provenance, and validation-profile snapshot.
- Handoff performs zero provider requests; SV decisions remain owned by the selected validation profile.

### Keyword Metrics Engine Phase 7 — PASS

- Handoff references immutable evidence IDs, preserves targeting/provider identity, snapshots the selected profile, supports subsets, and performs zero provider requests.
- Migration head: `c3keywordhandoff`; handoff tests passed.

### Keyword Metrics Engine Phase 8 — started

- Added profile-owned population/SV enablement flags and optional SV minimum.
- Added policy tests proving the same stored SV can produce different decisions under thresholds 100, 260, and 1,000 without provider access.

### Keyword Metrics Engine Phase 8 — closure checks added

- Missing enabled SV now returns explicit `MISSING_EVIDENCE` semantics.
- Disabled population/SV gates return explicit `NOT_APPLICABLE` semantics rather than fake PASS evidence.
- Added regression coverage for immutable profile snapshots and historical policy context.

### Keyword Metrics Engine Phase 8 — PASS

- Threshold policy, immutable Run context, missing-evidence semantics, and independently disabled gates: PASS.
- Focused closure tests: 10 passed; AST compilation: PASS; `git diff --check`: PASS.

### Keyword Metrics Engine Phase 9 — started

- Verified official Google Ads facts: `GenerateKeywordHistoricalMetrics` accepts up to 10,000 keywords and up to 10 geo targets; language and geo resource names are explicit; responses include query text, close variants, historical metrics, competition, bid ranges, and optional average CPC.
- Added transport-independent request construction and response mapping, plus OAuth/config fields. Live transport remains disabled.

### Keyword Metrics Engine Phase 9 — contract/mapping PASS

- Google request construction, geo/language mapping, close-variant identity, historical metric mapping, and optional CPC/bid fields: PASS.
- Added boundary tests for null optional fields, 10,000/10,001 batch handling, geo limits, secret safety, disabled/unapproved transport, and zero-cost semantics.
- Real Google transport remains intentionally pending external Manager account, developer-token access, OAuth setup, and explicit approval.
- Remaining Phase 1 work: migration integration tests, current-evidence/cache pointers, API contracts, provider guards, and batch orchestration.

### Keyword Metrics Engine Phase 1 closure and Phase 2 — started

- Cache-free AST compilation check passed for all 37 backend Python files; the prior locked `__pycache__` issue was bypassed without altering cache files.
- Added `backend/app/providers/keyword_metrics.py` with provider-neutral protocol, deterministic mock provider, import-only provider, and transport-disabled Google Ads skeleton.
- Added disabled-by-default Google Ads configuration flags without enabling transport.
- No live Google Ads, DataForSEO, Moz, Ahrefs, or SV provider requests were made.
