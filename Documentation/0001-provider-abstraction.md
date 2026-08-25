# ADR 0001 — Provider Abstraction Is Mandatory

Status: Accepted

NicheForge must isolate search-volume, SERP, authority, reviews and monetization vendors behind internal interfaces. Business rules may not directly call vendor HTTP endpoints. This prevents vendor lock-in, enables CSV/manual fallbacks, supports testing and allows providers to change without rewriting the validation engine.
