# NicheForge — Multi-City Search Volume Scaling & Operational Readiness

## Purpose

NicheForge’s Search Volume engine supports large keyword-by-city research while preserving evidence identity, provider provenance, currency normalization, cache reuse, and Rank & Rent policy separation.

The central design principle is:

> Search-volume evidence is acquired and persisted independently. Validation profiles decide how that evidence is used.

Low-volume evidence remains valid evidence. A profile may classify it as below threshold without deleting, refetching, or mutating the stored provider observation.

## Accepted multi-city architecture

The engine accepts arbitrary keyword and location inputs. Product-level limits are not imposed; provider limits are internal chunking constraints.

For each structured location, the engine resolves or reuses the canonical geo mapping, builds a targeting-aware cache identity, bulk-loads existing batch items, inserts missing items in chunks, bulk-loads fresh evidence, excludes cache hits, groups unresolved keywords by target, splits provider requests, persists immutable evidence, and applies Rank & Rent policy only to selected evidence.

Cities are never merged into a single provider target. Language and targeting identity remain part of the request and cache contract.

## RPC planning

The planner is deterministic and network-free. With the current internal keyword chunk size of 10,000:

| Input | Planned batches |
|---|---:|
| 1,000 keywords × 1 city | 1 |
| 1,000 keywords × 10 cities | 10 |
| 1,000 keywords × 100 cities | 100 |
| 10,001 keywords × 1 city | 2 |
| 15,000 keywords × 10 cities | 20 |
| 1,000 keywords × 10 cities × 2 languages | 20 |

Provider batching is target-isolated and language-aware. A cache hit never consumes a provider batch.

## Cache and identity guarantees

Evidence identity includes submitted keyword, normalized keyword, provider, language, country, location target, and targeting context. Country and worldwide results cannot collide.

The engine reuses fresh compatible evidence, never refetches it, preserves historical observations, keeps provider-returned keyword identity separate from submitted identity, preserves unmapped and failed states, and performs bulk cache filtering rather than one evidence query per combination.

## Persistence scaling

`KeywordMetricBatchItem` rows are bulk-loaded and missing rows are inserted in 1,000-row chunks. Query and immutable evidence identifiers are assigned before persistence where appropriate, avoiding per-result flushes for generated IDs.

Long-running orchestration uses bounded persistence checkpoints. ORM instances are retained across those checkpoints without expiration-driven refresh queries. This prevents status updates from producing one implicit `SELECT` per logical result.

## FX and monetary normalization

Provider currency is preserved as received. Customer currency is resolved from verified provider metadata, and USD fields are derived separately through persistent FX evidence.

For one orchestration run, the applicable FX rate is resolved once and reused with the same provenance for all results. Provider monetary values are not rewritten, USD CPC and bid fields remain separate derived values, and Rank & Rent thresholds do not alter monetary evidence.

## Scale acceptance benchmark

The exact 100,000-combination mock benchmark completed with:

```text
logical combinations: 100,000
planned provider batches: 100
actual mock provider batches: 100
FX resolutions: 1
runtime: 120.2 seconds
SQL statements: 705
flushes: 303
commits: 102
evidence rows: 100,000
batch items: 100,000
report entries: 100,000
external requests: 0
```

The benchmark ceiling was 180 seconds, leaving approximately 59.8 seconds of headroom.

The intermediate SQL profile demonstrated the persistence improvement:

```text
10,000 combinations before lifecycle fix: 10,023 SELECTs
10,000 combinations after lifecycle fix:       22 SELECTs
```

## Functional acceptance status

Accepted:

- multi-city provider batching;
- cache-first filtering;
- target and language isolation;
- batch-item bulk lookup and insertion;
- bounded flush and commit behavior;
- single-run FX resolution;
- ORM expiration/autoflush handling;
- immutable evidence persistence;
- explicit unmapped and failed states;
- 100,000-combination functional execution;
- 100,000-combination performance under 180 seconds;
- zero external provider requests during benchmark validation.

## Remaining operational safeguards

The following are separate hardening work, not blockers to the accepted scalability path:

1. Centralized Google customer rate limiting at the provider invocation boundary.
2. Configurable daily operation-budget guard based on actual/planned RPC operations.
3. Persisted per-chunk `ProviderCall` telemetry with target, language, chunk index, keyword count, attempt, timing, outcome, and operation count.
4. Public zero-network request preview exposing combinations, cache savings, target count, language count, chunk size, and planned RPC count.
5. Paginated result retrieval for very large API responses where returning every expanded result synchronously is unnecessary.

These safeguards must not change the accepted batching algorithm or evidence semantics.

## Safety requirements

Operational controls must preserve no silent provider fallback, no unauthorized retries, secret-safe logs and telemetry, truthful planned/attempted/successful/blocked/failed operation accounting, cache reuse before transport, explicit circuit-breaker behavior, and no automatic SERP, Moz, Ahrefs, DataForSEO, KD, population, or Rank & Rent calls from standalone Search Volume research.

## Checkpoint

The accepted batching and scale-performance checkpoint is committed as:

```text
2f52895 — Optimize multi-city batching at 100k scale
```

The next phase should add operational safeguards around this stable core rather than redesigning provider batching or persistence.
