# NicheForge UI/UX Redesign Roadmap

## Purpose

This is the canonical UI/UX roadmap for NicheForge. It turns the evidence-first backend into a clear product workflow while preserving the separation between Search Volume evidence and Rank & Rent policy.

## Principles

- Evidence is displayed truthfully; missing data is never fabricated.
- Search Volume is neutral research and does not reject low SV.
- Rank & Rent is a separate policy-driven workflow consuming stored evidence.
- Location is a targeting control, not a redundant results-table column.
- Only backend-derived USD fields receive `$` formatting.
- Loading, partial, unavailable, blocked, and error states are explicit.
- Large jobs show progress, cache state, batch identity, and resumable status.

## Completed UI foundation

- App shell, overview page, navigation, and consistent cards/forms/buttons.
- Search Volume workspace with multiline keyword input and parsed count.
- Global/Worldwide and country targeting with unsupported-country blocking.
- TXT/CSV keyword import with case-insensitive deduplication.
- Results table without the redundant location column.
- SV, trend, competition, CPC, low bid, and high bid presentation.
- Low/medium/high competition color treatment.
- Compact and expanded monthly trend bars with exact hover/focus tooltips.
- Commercial Insights with rounded clicks and “Projected Traffic Value” wording.
- Copy Results and CSV export with derived metrics.

## Phase UI-1 — App shell and overview

Status: complete. Maintain responsive navigation, page hierarchy, status indicators, and no unnecessary horizontal scrolling.

## Phase UI-2 — Search Volume Research workspace

Status: substantially complete; polish and broader capability remain tracked.

### Form

- Multiline keywords with visible parsed count and duplicate handling.
- Searchable country/region/city selector.
- Worldwide is a distinct target.
- Language selection comes from a capability registry.
- Provider/network remain under Advanced settings.
- Authenticated state and allowance/capacity feedback appear before execution.
- Submit states: ready, validating, queued, researching, complete, blocked, failed.

### Results

`Keyword | SV | 12M Trend | Competition | Avg. CPC | Low Bid | High Bid`

- No location column at normal desktop widths.
- Sort/filter controls and visible zero-SV rows.
- Explicit unmapped, partial, and unavailable states.
- Blue low, orange medium, and red/purple high competition colors.

### Trends and commercial values

- Monthly bars show real values; hover/focus shows month, year, and searches.
- Tooltips escape card/table overflow and remain visible.
- Zero-search months remain real zeros; missing months are not invented.
- Expanded chart and Commercial Insights table show Position, CTR, Estimated Clicks, and Projected Traffic Value.
- Projected Traffic Value is advertising-equivalent modeled value, not revenue.

### Actions

- Copy visible results as TSV.
- Export visible/all results to CSV with provenance and derived metrics.
- Import TXT/CSV with accepted, rejected, and duplicate counts.
- PDF export remains a separate task.

### Search Volume → Rank & Rent handoff

This bridge is part of the remaining UI-2 product work and must not trigger
SERP, Moz, KD, or other provider calls by itself.

- Configurable independent handoff threshold; initial default `SV >= 260`.
- Detect qualifying rows locally from stored/returned evidence.
- Show a non-blocking “Rank & Rent candidates” prompt with Review Candidates
  and Send All actions.
- Show a neutral `R&R Candidate` badge, never PASS or IDEAL before validation.
- Provide per-row Send to Rank & Rent, multi-select Send Selected, and Send All
  Qualifying actions.
- Review candidates in a drawer/modal before handoff, including threshold,
  selected rows, target project, and validation profile.
- Detect already queued, already validated, previously rejected, and new
  candidates before creating duplicates.
- Reuse the original SV evidence ID, target, language, provider, freshness,
  trend, CPC/bid fields, and source batch in the handoff.
- Record a handoff ledger event with source batch, user, evidence ID, target,
  project, profile, and timestamp.
- Keep handoff separate from the Rank & Rent profile minimum SV gate; a row may
  be handed off at 260 and later fail a profile requiring 300.

### Search Volume table productivity

- Sort SV by default, descending, ascending, and optionally restore original
  order by clicking the SV header.
- Preserve numeric zero separately from null/unavailable/UNMAPPED during sort.
- Quick filters: All, SV at/above handoff threshold, SV below threshold, Mapped,
  and Unmapped, plus a configurable minimum-SV filter.
- Add Copy Search Volumes Only, Copy Keywords Only, Copy Keyword + SV, and Copy
  Full Results actions using TSV where tabular output is useful.
- Support row selection, select all visible, select all qualifying, clear
  selection, and explicit Visible/Selected/All scopes for copy, export, and
  handoff actions.
- Preserve active filter and sort state when the user chooses an action.

### Search Volume statistics additions

Show Total Keywords, Mapped, Unmapped, Median SV, and R&R Qualifying count.
Clicking the qualifying count filters the results to qualifying rows. Counts
must remain evidence summaries, not Rank & Rent decisions.

## Phase UI-3 — Authentication and usage experience

Status: foundation implemented; product polish follows quota rollout.

- Login/session-expiry states.
- Authenticated Search Volume requests.
- Allowance panel: daily allowance, consumed, reserved, available, and request requirement.
- Clear user-quota versus provider-capacity errors.
- Admin-only quota/usage controls.

## Phase UI-4 — Rank & Rent Engine/UI

Status: next product phase.

Workflow: `Population → Search Volume → SERP Acquisition → DA Gate → Deeper SERP Analysis → KD → Result/History`

- Validator form for niche, city source, population, SV, DA, KD, provider, cache, and freshness policies.
- Zero-network preview and estimated work summary.
- Candidate table with population, SV, trend, SERP, weak-domain evidence, KD, status, and reason codes.
- Fail-fast stage display with PASS, IDEAL, REJECTED, INCOMPLETE, and RETRYABLE states.
- Expandable evidence lineage and visible manual overrides.
- Immutable run history, profile snapshots, recalculation reuse, provenance, and exports.
- Accept Search Volume Research as an explicit candidate source, preserving the
  handoff evidence lineage and selected project/profile.

## Phase UI-5 — SERP evidence workspace

Status: later. Show rank-preserved organic rows, domain evidence, whole-SERP proxy review, exact-domain Moz reconciliation, manual validation, opportunity recall, and false-negative reporting.

## Phase UI-6 — Monetization and learning surfaces

Status: later. Add offer/buyer state, built-site outcomes, revenue learning, and secondary scoring only after sufficient user-owned calibration data.

## Acceptance checklist

- TypeScript and production build pass.
- No hydration/overflow errors.
- Worldwide and supported country targets work; unsupported targets are explicit.
- USD labels only appear with valid USD evidence.
- Trend tooltips are visible and exact.
- Zero/partial/unavailable states remain truthful.
- Import, copy, and CSV export preserve evidence identity.
- Rank & Rent policy changes reuse stored evidence without refetch.
- Visual-only and preview interactions make no provider calls.
### UI-4 Search Volume handoff bridge — implemented checkpoint

The Search Volume workspace now exposes immutable evidence IDs, a configurable 260+ qualification threshold, R&R Candidate labels, selectable qualifying rows, explicit handoff to the existing validation endpoint, SV-only copy, and ascending/descending SV sorting. Handoff is evidence-preserving and provider-free; Rank & Rent remains responsible for downstream SERP/DA policy.
### Phase UI-3 — Authentication and usage experience

Status: IMPLEMENTED / FROZEN. Single-user development mode is configurable locally while the multi-user authentication and quota architecture remains preserved for future deployment.

NEXT ACTIVE PRODUCT PHASE: UI-4C — Live Rank & Rent Validation Run Workspace.
