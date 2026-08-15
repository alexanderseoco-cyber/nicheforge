# NicheForge Search Volume & Rank-and-Rent Validation Workflow

## Governing principle

Search-volume evidence is data. Rank & Rent eligibility is policy.

The same immutable Google Ads evidence may be displayed by the standalone SV
Checker and evaluated by one or more Rank & Rent validation profiles without
being deleted, invalidated, overwritten, or refetched because of a threshold.

## Workflow

```text
keyword + targeting
        ↓
Google Ads/provider boundary
        ↓
immutable SV evidence + monthly history
        ├── Standalone SV Checker: display every valid result
        └── Rank & Rent profile: apply configurable minimum SV policy
                                      ↓
                              downstream validation pipeline
```

## Standalone SV Checker

The standalone research tool must:

- accept arbitrary keywords and targeting;
- preserve valid results including `0`, `10`, and other low values;
- show average monthly searches without applying a rejection threshold;
- expose the provider, targeting, provenance, cost, cache state, and evidence identity;
- expose the available monthly trend;
- preserve partial or missing history honestly;
- never call Google again merely because a result is below a validation threshold.

## Rank & Rent validation policy

The Rank & Rent workflow consumes stored evidence and applies the active
validation profile. The default minimum is configurable and currently expected
to be `260`.

```text
SV >= configured minimum  → eligible for downstream pipeline
SV < configured minimum   → BELOW_SV_THRESHOLD for this validation run
missing SV evidence       → MISSING_EVIDENCE
```

`BELOW_SV_THRESHOLD` is a policy result, not invalid evidence. The underlying
evidence remains reusable by the standalone checker, later profiles, history,
and recalculation.

## Immutable evidence and recalculation

- Evidence records are append-only and retain provider provenance.
- Run/profile snapshots retain the threshold used for their decision.
- Changing the threshold recalculates from stored evidence with zero provider calls.
- Completed historical Runs do not change when later profiles or thresholds change.
- A candidate subset may be handed to validation; researching a large set does
  not imply handing every item downstream.

## Monthly-history contract

Google Ads monthly history is normalized at the provider boundary:

```json
{
  "year": 2026,
  "month": 8,
  "searches": 10
}
```

Requirements:

- preserve every provider-returned valid observation;
- support numeric and enum month representations;
- sort oldest to newest;
- do not fabricate or interpolate months;
- preserve fewer than 12 observations as partial history;
- classify history as `COMPLETE_12M`, `PARTIAL`, or `MISSING`;
- expose the same provider-neutral structure through the backend and frontend.

## UI behavior

The standalone SV workspace displays:

```text
Keyword | Location | SV | 12M Trend | CPC | Competition | Provider
```

The trend may be a compact chart or expandable month/value list. Low SV is
shown, not hidden. The current workspace also supports a default United States
target, one semantic `Global / Worldwide` target, TXT/CSV keyword import with
case-insensitive deduplication, filtered results, TSV copy, and CSV export.

Commercial Insights remain in the expanded row and use the user-facing term
`Projected Traffic Value` for the modeled `SV × CTR × CPC` estimate. It is an
advertising-equivalent estimate, not projected revenue. Display values round
estimated clicks without changing persisted calculations.

The Rank & Rent workflow additionally shows eligibility and reason codes,
including `BELOW_SV_THRESHOLD`, without changing the stored evidence.

## Implementation phases

### Phase 1–5 — Architecture and policy separation

- verify evidence acquisition remains independent of validation policy;
- preserve standalone research behavior;
- apply thresholds only during validation handoff/recalculation;
- preserve immutable Run/profile snapshots;
- add API/UI distinction between evidence and eligibility;
- add regression coverage for low SV, missing evidence, disabled gates, and
  threshold changes.

### Phase 6 — Live-response trend mapper repair

- inspect the actual Google Ads v25 protobuf response shape;
- map monthly values into the normalized contract;
- preserve numeric and enum months;
- preserve partial histories and provider-returned zero values;
- verify CPC/bid micros conversion remains correct;
- do not make a live request during the implementation phase.

### Phase 7 — Regression closure

Run targeted tests, full relevant tests, AST compilation, frontend TypeScript
validation, frontend build validation, and `git diff --check`.

Required regression cases include:

- standalone SV `10` remains displayable;
- Rank & Rent minimum `260` produces `BELOW_SV_THRESHOLD`;
- the same evidence can be evaluated under multiple thresholds;
- threshold recalculation performs zero provider calls;
- historical Runs remain unchanged;
- monthly history persists, sorts, and remains frontend-compatible.

### Phase 8 — Controlled Albany confirmation

Using the already persisted Albany, Georgia evidence:

- standalone SV Checker displays its SV and trend;
- Rank & Rent with minimum SV `260` returns `BELOW_SV_THRESHOLD`;
- the candidate is not sent downstream;
- no additional Google request occurs for the policy decision;
- Google transport is restored to disabled after any separately authorized live
  confirmation.

## Provider boundaries

This workflow does not authorize or imply calls to DataForSEO, Moz, Ahrefs,
SERP, population, KD, backlink, or validation providers. Google transport is
disabled by default and requires explicit approval for any live operation.

## Current UI completion notes

- Completed: Commercial Search Value and Projected Traffic Value presentation,
  rounded click display, default US target, Global / Worldwide alias, keyword
  import, filtered results, TSV copy, and CSV export.
- Pending: historical recalculation/backfill for evidence created before the
  verified currency/FX contract, and expansion of the language capability
  registry beyond the currently validated language set.
- Stale provider evidence must not be relabeled in place; recalculation must
  preserve provider-currency values and use the explicit derived-evidence path.

## Definition of done

- Evidence and policy are demonstrably separate.
- Standalone SV displays all valid values.
- Rank & Rent applies configurable minimum SV policy.
- `BELOW_SV_THRESHOLD` is explicit and non-destructive.
- Threshold changes reuse stored evidence without provider calls.
- Monthly history is normalized, persisted, exposed, and tested.
- Albany acceptance test proves both consumers use the same evidence correctly.
- No unrelated provider activity occurs.
