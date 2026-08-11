# Moz Provider Contract Status

Research-only boundary. No live Moz endpoint or credential is activated until each required contract detail is supported by current official Moz documentation or authorized account documentation.

| Area | Status | Verified detail | Source/date |
|---|---|---|---|
| Authentication | UNVERIFIED | No endpoint/auth scheme is approved for implementation. | Official contract review pending / 2026-08-11 |
| DA | UNVERIFIED | Canonical field is supported only through imported evidence for now. | Official contract review pending / 2026-08-11 |
| PA | UNVERIFIED | Not treated as a live capability. | Official contract review pending / 2026-08-11 |
| Spam Score | UNVERIFIED | Not treated as a live capability. | Official contract review pending / 2026-08-11 |
| Linking domains | UNVERIFIED | Not treated as a live capability. | Official contract review pending / 2026-08-11 |
| Backlinks | UNVERIFIED | Not treated as a live capability. | Official contract review pending / 2026-08-11 |
| Keyword Difficulty | UNVERIFIED | Moz remains the intended default provider, but request/field contract is not approved. | Official contract review pending / 2026-08-11 |
| Batch target limit | UNVERIFIED | No batch size is hardcoded. | Official contract review pending / 2026-08-11 |
| Rows/quota | UNVERIFIED | No quota or per-row consumption assumption is used. | Official contract review pending / 2026-08-11 |
| Rate limits | UNVERIFIED | No rate limit is hardcoded. | Official contract review pending / 2026-08-11 |
| Subscription tiers | UNVERIFIED | No tier is treated as available. | Official contract review pending / 2026-08-11 |
| Overage | UNVERIFIED | No overage behavior is assumed. | Official contract review pending / 2026-08-11 |
| KD billing | UNVERIFIED | No claim is made that KD is free or bundled with DA. | Official contract review pending / 2026-08-11 |

Third-party pricing or endpoint claims must not promote any row above `UNVERIFIED`.

## Parallel Ahrefs DR proxy boundary

Ahrefs DR is implemented as a separate high-recall proxy and is not Moz DA evidence. The verified official Ahrefs contract is documented at [Ahrefs Domain Rating free API](https://docs.ahrefs.com/en/api/reference/public/get-domain-rating-free): `GET https://api.ahrefs.com/v3/public/domain-rating-free`, required `target`, `Authorization: Bearer <token>`, response `domain_rating.domain_rating`, license/warning metadata, zero API-unit consumption, and required attribution `Domain Rating by Ahrefs`.

No Ahrefs key is configured and no live Ahrefs request has been made. Proxy calibration remains `UNCALIBRATED_HIGH_RECALL`; no DR-to-DA conversion is assumed.
