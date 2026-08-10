# NicheForge Task Completion Status

**Current phase:** Phase 1A — Durable Mock-Provider Validation Core  
**Status:** Checkpoint A in progress; paused for review  
**Last updated:** 2026-08-10

## Workflow rule

Every new change, completed task, milestone, or blocked task must update this status file. The update must record:

- task or milestone completed;
- files changed;
- validation actually executed;
- remaining work or blockers;
- corresponding section of `docs/ORIGINAL_PLAN_OF_IMPLEMENTATION.md` reconciled.

The implementation plan and this status file must remain synchronized. A phase may not be marked implemented until its required work and validation are complete.

## Latest update

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
