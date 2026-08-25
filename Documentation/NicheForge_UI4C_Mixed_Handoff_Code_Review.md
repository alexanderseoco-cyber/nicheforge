# NicheForge UI-4C Mixed Handoff Code Review

Read-only diagnostic packet generated 2026-08-16. No application behavior was
changed by this export and no provider requests were made.

## Review scope

The complete source of the relevant flow is maintained in these files:

- `backend/app/models/entities.py` — `CandidateEntity`, `ProjectCandidate`,
  `Run`, `RunCandidate`, `KeywordMetricEvidence`, and handoff models.
- `backend/app/api/routes.py` — handoff creation/read, scope classification,
  attachment, preview, and run serialization.
- `backend/app/services/identity.py` — canonical identity and identity key.
- `backend/app/services/validation_scope.py` — local/general classification.
- `backend/app/services/run_pipeline.py` — RunCandidate creation/execution.
- `backend/app/services/authority_evaluation.py` — authority grading.
- `backend/app/schemas/domain.py` — request/response contracts.
- `frontend/app/research/search-volume/page.tsx` — handoff navigation.
- `frontend/app/rank-rent/validator/page.tsx` — initialization, partial attach,
  location confirmation, preview, and readiness state.

## Migration revisions

`c15projectcandidatesvevidence` has parent `c13userquotas` and adds
`project_candidates.search_volume_evidence_id`.

`f2twopipelinescope` has parent `c15projectcandidatesvevidence` and adds:

- nullable `candidate_entities.city_id`;
- `candidate_entities.validation_scope`;
- `project_candidates.validation_scope`;
- `project_candidates.scope_reason`;
- `run_candidates.validation_scope`;
- `run_candidates.authority_opportunity_reason`.

Alembic currently reports one head: `f2twopipelinescope`.

## Identity and reuse facts

`CandidateEntity` identity is based on `identity_key(canonical_identity(...))`.
Local canonical identity uses the city/geographic identity. General canonical
identity uses the country identity. `ProjectCandidate` reuse is keyed by the
unique constraint `(project_id, candidate_entity_id)`. Evidence is linked
separately through `search_volume_evidence_id`.

`PROJECT_CANDIDATE_EVIDENCE_CONFLICT` is raised when an existing ProjectCandidate
for the same project and CandidateEntity has a non-null evidence ID different
from the incoming handoff evidence ID. This preserves immutable evidence lineage
and prevents silent evidence replacement.

## Mixed attachment behavior

The current attach route classifies handoffs independently. Local ambiguous
handoffs return `LOCAL_LOCATION_REQUIRED` with city candidates. General handoffs
materialize as `GENERAL_READY` with a nullable city. The response includes
`results` and `summary` fields while preserving created/existing counts and
ProjectCandidate IDs.

Expected mixed response:

```text
tree service albany       LOCAL_LOCATION_REQUIRED
stylish text generator    GENERAL_READY
fancy text generator      GENERAL_READY
```

## Current database facts

Current matching handoffs:

| handoff_id | keyword | evidence_id | country | target |
|---|---|---|---|---|
| 365c95dd-c7c7-4e97-bbb0-f7a344525628 | tree service albany | 1b94fae5-ac60-45b4-9a47-b5739ca7c2cf | US | country US |
| 54acd6df-643c-4987-b96a-b5ec2fae16d8 | stylish text generator | 3f791da7-3019-424f-8a49-ea657d7339d8 | US | country US |
| a4e4181e-f8c3-4100-a69b-db72525a35e0 | fancy text generator | ffef9101-6389-4994-ae7c-fe793ab417da | US | country US |

Current relevant project IDs include:

- `4bdce75b-9c1c-4d7f-9c02-596f0b5bc2e7` — historical candidates/run data;
- `b22691e9-d2fb-45f2-913c-9399bde68dd6` — mixed general candidates;
- `18a135fa-d24c-47b5-a142-eef030b20ebe` — current empty test project.

Current handoff counts are one each for `tree service albany`,
`stylish text generator`, and `fancy text generator`; no duplicate handoffs
remain for these exact spellings.

## Exact conflict interpretation

The observed conflict occurred when the Validator reused a project while
processing historical duplicate handoffs for the same logical keyword. The
incoming and existing records shared the same `(project_id, candidate_entity_id)`
identity but referenced different immutable Search Volume evidence IDs. The
conflict is therefore an evidence-lineage protection, not a provider failure.

The current clean three-handoff set has no duplicate handoff records. A fresh
empty project should be used for browser acceptance.

## Tests and provider policy

Focused handoff, mixed attachment, scope, and authority tests were run during
the diagnostic sequence. Provider traffic remained zero:

```text
Google Ads: 0
DataForSEO: 0
Moz: 0
Ahrefs: 0
FX: 0
Other: 0
```

This packet is uncommitted and is intended for external architectural review.
