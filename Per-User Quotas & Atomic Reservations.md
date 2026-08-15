# NicheForge — Per-User Quotas & Atomic Reservations

## Purpose

This is the final infrastructure phase before returning to the Rank & Rent roadmap. It adds authenticated user/provider allowance controls without billing, subscriptions, Stripe, extension implementation, or new provider infrastructure.

## Accounting boundaries

- `ProviderCall.operation_count` is authoritative for actual Google consumption.
- `UserProviderUsage` attributes that consumption to the authenticated `user_id`.
- `RunReservation` represents pre-execution capacity, not consumption.
- Unused reservation capacity is released at completion.
- A retry/additional RPC must atomically acquire additional user and provider capacity before it is attempted.
- Bonuses are immutable grants and are protected by the reservation transaction.

## Scope and safety

- Default and per-user rolling-24-hour Google Ads allowances.
- Expiring immutable bonuses, atomic reservations, and effective allowance `min(user available, provider available)`.
- Authenticated Search Volume preview, research, refresh, and multi-city routes.
- Identity comes only from `get_current_user()`, never request JSON.
- Preview is zero-network and creates no reservation, bonus consumption, usage, or ProviderCall records.
- Existing anonymous historical evidence remains untouched.
- No billing/subscriptions and no provider requests during implementation or validation.
- Changes remain uncommitted for review.

## Acceptance

Validate defaults, overrides, expired bonuses, disabled providers, concurrent reservation behavior, partial consumption/release, identity-based route protection, admin isolation, and preservation of provider, batching, FX, Commercial Insights, and Rank & Rent behavior. After acceptance, backend infrastructure work stops and Phase 3 Rank & Rent work resumes.
