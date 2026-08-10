# NicheForge API Keys and Provider Access Rules

## Purpose

This document is a workflow control for provider credentials, API access, billing modes, and paid-call authorization. It is part of the project source-of-truth workflow and must be reviewed before live-provider implementation.

## Credential rules

1. Never commit API keys, passwords, OAuth tokens, refresh tokens, developer tokens, account IDs, or production database credentials.
2. Store credentials only in environment variables, a local untracked `.env`, or an approved secrets manager. `.env.example` may contain names and placeholders only.
3. Use separate credentials/configuration for `SANDBOX`, `TRIAL`, and `PRODUCTION`.
4. Production mode is disabled by default and requires explicit configuration plus a budget ceiling.
5. Sandbox and mock requests must never be represented as real production evidence or real provider cost.
6. Provider credentials must remain behind provider adapters; the validation engine must never read vendor secrets directly.
7. Logs, exceptions, exports, events, and ProviderCall metadata must redact credentials and authorization headers.
8. Credentials must not be placed in the Chrome extension.
9. A missing, invalid, expired, or ambiguous credential is a provider configuration failure; the system must not fabricate a response or silently switch providers.

## Provider ownership

| Metric/work | Preferred provider/source | Evidence identity | Status |
|---|---|---|---|
| Localized organic SERP | DataForSEO | `dataforseo_api` / sandbox variant | Planned boundary |
| Search volume | Imported KE, DataForSEO, or later Google Ads by explicit Run policy | provider-specific | Policy required |
| DA/PA/Spam/link metrics | Official Moz access or Moz export | `moz_api` or `moz_csv` | API contract unverified |
| Keyword Difficulty | Moz by default; Ahrefs remains separate | `moz_api`/`moz_csv` or `ahrefs_csv` | Provider-specific |

Conflicting SV observations are retained separately and are never averaged. Ahrefs KD cannot satisfy a Run requiring Moz KD. Provider selection is snapshotted into each Run.

## Operational modes

- `SANDBOX`: provider sandbox/sample behavior; cost recorded as zero/test; never treated as real Google/Moz evidence.
- `TRIAL`: real credentials and real account balance; strict configurable spend ceiling; default ceiling must not exceed the verified available trial balance.
- `PRODUCTION`: disabled until explicitly enabled with credentials, budget, and manual paid-call approval.

DataForSEO Sandbox, trial credit, minimum top-up, refund, balance-expiry, and current prices are commercial facts that must be verified against current official documentation/account access before being relied upon. The project must not hardcode them as permanent guarantees.

Current official DataForSEO documentation confirms that Sandbox requests are not charged and return dummy/sample data. The official SERP overview also documents Standard and Live methods, configurable depth/cost behavior, and a stated limit of up to 2,000 POST/GET calls per minute with up to 100 tasks per POST; current account pricing and trial terms remain configuration/account-verification items. Moz endpoint, quota, batching, KD, and billing details remain `UNVERIFIED` pending current official Moz material or account documentation.

## Paid-call authorization

Before paid execution, preview must show candidate count, reusable/imported SV, required SERPs, estimated provider cost, cached/fresh authority targets, adaptive target range, and expected downstream KD work. The default behavior is manual approval of the estimated paid run. No silent cross-provider fallback is allowed; fallback requires an explicit approved provider policy.

## Cost and quota rules

1. Pricing, units, batching, quota consumption, rate limits, and billing are provider configuration, not business constants.
2. Every live call records provider, mode, operation, request dimensions, units, estimated cost, actual cost when available, currency, outcome, and cache-hit state.
3. Historical Run costs never change when pricing configuration changes later.
4. Moz consumption must not be estimated as free or shared across DA/PA/KD until the official contract confirms it.
5. DataForSEO Standard Queue is the planned bulk default; Priority/Live remain configurable.
6. Development must work with mocks and DataForSEO Sandbox without requiring the normal production top-up.

## Required verification before live activation

Document official/current evidence for authentication, DA, PA, Spam Score, linking domains/backlinks, KD, target/batch limits, rate limits, quotas, plans, per-row charging, shared metrics, overages, and failure behavior. Unknown items must be marked `UNVERIFIED`; endpoints and billing must never be invented.

## Approved DA opportunity semantics

- Weak domain definition: `DA < 10` by default, configurable.
- `0–3` confirmed weak domains: `PRIMARY_REJECTED`.
- `4` confirmed weak domains: `PASS` / viable opportunity.
- `5+` confirmed weak domains: `IDEAL` / strongest opportunity classification.
- Minimum weak and ideal weak thresholds are independently configurable and snapshotted per Run.
- KD remains downstream of the DA primary stage and cannot rescue a DA failure.

## Adaptive authority rules

`ADAPTIVE` is the planned bulk default; `FULL` remains configurable. Adaptive evaluation may consume compatible fresh cache first, fetch unknown/stale targets in configurable small batches, and stop only when PASS, IDEAL, or mathematical failure is certain. Unchecked positions are never counted as evaluated. Runs must preserve evaluation mode, organic depth, evaluated/cached/fetched target counts, unchecked count, confirmed weak count, thresholds, primary result, and opportunity classification.

## Current implementation boundary

This document records the approved rules. Live Moz/DataForSEO/Google Ads calls remain disabled until the Provider Readiness checkpoint verifies official contracts, implements safe configuration, and passes its acceptance tests.
