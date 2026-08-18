# NicheForge Provider Cost Reduction

## Approved telemetry direction

NicheForge will measure provider economics before changing provider behavior. The
first implementation checkpoint is limited to contract tests and an additive,
nullable telemetry schema on the existing ProviderCall model.

Telemetry must remain observational. It must not decide cache reuse, freshness,
provider execution, retries, gates, ordering, transactions, or evidence lineage.
Telemetry failures must never fail validation.

## Current scope

Checkpoint 1 added no runtime instrumentation. Checkpoint 2 now adds Moz-only
observational fields to existing authority ProviderCall records. It still does
not split Moz DA/PA, correct the legacy "mock" cache dimension, change cache
keys, alter provider behavior, or touch Ahrefs, backlinks, SERP batching, KD, or
the frontend.

The approved future measurements distinguish logical demand, unique normalized
targets, cache hits/misses/staleness, evidence reuse/creation, provider items,
batches, actual HTTP requests, attempts, retries, and known costs.

## Storage decision

ProviderCall is the existing request-level infrastructure and will be extended
additively rather than introducing a parallel telemetry table. Existing fields
are reused for provider, operation, cache key, cache hit, costs, attempt number,
duration, provider reachability, operation count, and run/candidate linkage.

New fields are nullable aggregate telemetry only. Existing rows remain valid and
no historical data is rewritten.

## Moz future measurement contract

Without splitting DA/PA, future instrumentation should measure authority
occurrences, unique exact URLs, unique normalized root domains, repeated exact
URLs, same-domain/different-URL occurrences, cache outcomes, submitted items,
batches, HTTP requests, retries, reused/new AuthorityEvidence, and DA/PA
availability.

No DA-domain cache or PA-URL cache is introduced until real usage demonstrates
that the migration and lineage cost is justified.

## Future phased work

1. Lock current provider behavior with regression tests.
2. Add the nullable ProviderCall schema.
3. Instrument one provider family at a time, starting with Moz. (Current.)
4. Collect real Local and General validation data.
5. Recalculate the 100-candidate cost model.
6. Consider provider-identity cache-key versioning with legacy reads.
7. Consider DA-domain/PA-URL separation only if measured savings justify it.

The "mock" cache identity and authority split remain separate future
checkpoints.

## Current implementation status

The authoritative database is migrated to f6providercalltelemetry. Moz
authority operations record compact aggregate telemetry for cache reuse and
provider acquisition, including occurrence/URL/domain duplication counts,
provider items, batches, actual HTTP requests, evidence reuse/creation, and
provider identity. Existing request payloads, batching, cache decisions,
freshness, evidence lineage, and authority policy are unchanged.

Telemetry writes are best-effort and protected by a nested transaction boundary.
Telemetry failures are logged concisely and do not change candidate state or
poison the main validation session.

Moz candidate-level totals are stored once on an authority_summary ProviderCall
row. Reuse and batch rows are detail rows. Candidate totals must query the
authority_summary row; detail rows may be summed only for their own operation
metrics. Known zero counts are stored as zero, while NULL means not applicable,
not measured, or unknown.

Google Ads and SERP instrumentation are implemented; Ahrefs DR is instrumented
in C1D. Backlinks, KD, and gate-savings instrumentation are not implemented yet.

## C1A telemetry contract

ProviderCall telemetry is prospective and best-effort. A known zero is stored
as `0`; `NULL` means not applicable, not measured, or unknown. Cost confidence
uses `ACTUAL`, `PROVIDER_REPORTED`, `ESTIMATED`, `UNKNOWN`, or
`NOT_APPLICABLE`. `provider` identifies the adapter that executed the
operation; `actual_evidence_provider` identifies the provider of reused or
created evidence and must not be inferred from the runtime adapter.

Operation categories are `PROVIDER_ACQUISITION`, `CACHE_REUSE`,
`PARENT_EVIDENCE_REUSE`, and `SUMMARY`. Summary rows hold candidate/run
totals; acquisition/detail rows hold their own batches and HTTP requests and
must not be summed with summaries. Telemetry writes use a nested savepoint and
fail closed: a write or update failure cannot change provider execution,
validation state, retries, or evidence lineage.

For Google Ads cost reporting, CPC, bids, and competition values remain
business metrics and are never API acquisition cost. New Google Ads telemetry
uses `actual_cost = NULL`, `estimated_cost = NULL`, and `currency = NULL` when
the API charge is unknown, with `cost_confidence = UNKNOWN`. Older ProviderCall
rows may contain legacy `estimated_cost = 0.0` and `currency = USD`; those rows
are immutable and must not be interpreted as measured API cost.

Query-safe aggregation separates operation categories: sum provider items,
chunks, HTTP requests, returned items, and failed items from acquisition rows;
sum evidence reuse from `CACHE_REUSE` rows; and sum finalized created/missing
evidence only from acquisition rows. Logical and unique demand are aggregated
from their defined operation scope, not blindly across every row. NULL final
evidence counts remain unknown and are not converted to zero. API cost is
reported as unknown unless actual/provider-reported cost exists; CPC is never
used in that calculation.

## C1C DataForSEO SERP telemetry

SERP acquisition telemetry is one `ProviderCall` per actual SERP request;
`CACHE_REUSE` remains a separate zero-request row and parent recalculation reuse
remains `PARENT_EVIDENCE_REUSE`. Acquisition rows record one logical/unique
target, one provider item/task, one batch, and one HTTP request. Reuse rows have
zero provider items, batches, and HTTP requests.

SERP metadata records requested depth, observed usable organic depth, coverage
ratio, centralized evidence state, and compact provider status information.
`VALID`, `PARTIAL_VALID`, `INSUFFICIENT`, `PROVIDER_ERROR`, and
`INVALID_TARGET` retain the frozen classifier semantics. Snapshot creation is
counted as created evidence; organic result rows are not double-counted as
additional provider requests. DataForSEO API cost remains NULL/UNKNOWN unless
the provider directly reports a charge. Historical SERP ProviderCall rows and
snapshots are not backfilled or rewritten.

## C1B Google Ads measurement semantics

Prospective Google Ads acquisition rows remain one `ProviderCall` per provider
chunk. Their logical and unique counts describe that chunk only; they are not
candidate-wide totals. `provider_item_count` and `batch_size` count submitted
keyword targets, while `items_returned_count` and `items_failed_count` describe
the provider response for that chunk. `batch_count` is one for each acquisition
row and `http_request_count` is zero for mock transport or one for a live
outbound request. `http_request_sent` records that transport fact.

Cache reuse is represented separately by `CACHE_REUSE` rows. Reuse rows have
zero provider items, batches, and HTTP requests, and record reusable evidence
counts without being added to acquisition-row totals. Stale entries are misses
requiring acquisition, not successful reuse. Google Ads CPC and bid values are
business metrics, never API cost; API cost remains unknown where the provider
contract supplies no charge. Existing historical rows are not backfilled.

## C1D Ahrefs DR measurement semantics

Ahrefs DR is domain-level evidence. The existing production path normalizes and
deduplicates SERP rows by root domain, then performs one Ahrefs request per
provider-bound domain. C1D preserves that granularity and does not change
payloads, batching, retries, cache keys, freshness, gates, or evidence lineage.

Each acquisition request records one logical target and one unique normalized
domain, one provider item, one batch, and one HTTP request. A usable DR response
creates one `ProxyAuthorityEvidence` unit. A successful response without a
usable DR value is a successful provider operation with missing evidence, not a
transport error; no `ProxyAuthorityEvidence` row is created. The current
provider parsing keeps a genuine DR value of `0` distinct from an absent or
unusable value. DR has no meaningful partial state in the current one-domain
request contract, so `evidence_partial_count` is zero. Provider errors retain
their attempted-request accounting and missing-evidence count without
fabricating DR evidence.

Fresh 30-day Ahrefs evidence is represented by a separate `CACHE_REUSE` row:
zero provider items, zero batches, zero HTTP requests, `paid_attempt = false`,
and one reused evidence unit. Reuse rows are never summed with acquisition rows.
Historical Ahrefs evidence and ProviderCall rows are not backfilled.

The local Ahrefs response contract exposes Domain Rating but no direct monetary
request cost. Therefore C1D records `actual_cost = NULL`, `estimated_cost =
NULL`, `currency = NULL`, and `cost_confidence = UNKNOWN` for acquisition. A
sent request is not assumed to be charge-bearing, so `paid_attempt` remains
unknown for acquisition and false for cache reuse.

Telemetry writes use the accepted savepoint-isolated best-effort helpers. A
telemetry construction or persistence failure cannot cause a second Ahrefs
request, discard successful DR evidence, or alter the proxy decision. Query-safe
reports sum HTTP/items/evidence-created from acquisition rows and evidence
reuse only from `CACHE_REUSE` rows.

There is no distinct post-persistence telemetry-finalization phase in C1D;
final fields are updated immediately after the existing evidence persistence
boundary, so a separate post-persistence failure-injection scenario is not
applicable.

C1D is observational only. No Ahrefs optimization is justified until measured
provider-bound domains, requests, reuse, and costs are collected.

## C1E DataForSEO backlinks / referring-domains telemetry

The backlink path uses normalized root domains as its target identity. Existing
deduplication and the configured DataForSEO batch size are unchanged. Each
actual `/v3/backlinks/bulk_pages_summary/live` batch/task is represented by one
prospective `PROVIDER_ACQUISITION` ProviderCall; there is no candidate-wide
aggregate acquisition row. Batch-local logical, unique, submitted, returned,
failed, HTTP, and evidence counts therefore reconcile directly to provider
execution.

The canonical evidence unit is one `ProxyBacklinkFeatureEvidence` per normalized
domain. A mapped result creates one evidence unit; an unmatched or unusable
result is missing evidence. Provider-reported zero backlink or referring-domain
values remain valid evidence and are not treated as missing. The current model
has no separate partial canonical state, so partial count is zero where known.

Fresh reusable evidence produces separate `CACHE_REUSE` telemetry with zero
provider items, batches, HTTP requests, and acquisition cost, plus one reused
evidence unit per naturally reused domain. Reuse rows are excluded from
acquisition totals and never copy historical cost.

DataForSEO backlink cost is provider-reported from `task.cost`, falling back to
top-level `data.cost`. When present, acquisition telemetry stores the exact
amount, `cost_confidence = PROVIDER_REPORTED`, `estimated_cost = NULL`, and
`currency = USD` under the locally established DataForSEO contract. When absent,
all monetary fields remain NULL and confidence is UNKNOWN. `paid_attempt` is
true only when a provider-reported cost establishes a charge-bearing operation;
otherwise it remains NULL. Cache reuse always has `paid_attempt = false`.

Backlink telemetry uses savepoint-isolated best-effort writes. Telemetry failure
cannot alter provider execution, evidence persistence, retries, or candidate
behavior. Historical ProviderCall and backlink evidence rows are not rewritten.
Provider failures retain their original exception behavior while recording one
attempted batch row when the adapter exposes the attempted batch boundary. The
prospective per-batch rows must be reported separately from historical legacy
aggregate backlink rows; NULL cost is unknown, never monetary zero.
