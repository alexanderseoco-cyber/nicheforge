# NicheForge — Authentication/User Identity Foundation

## Purpose

Establish durable user identity above the accepted Google Ads provider-safety
layer (`d2ae13c`). This phase does not implement quotas, bonuses, billing, or
provider reservations.

## Scope

1. Audit the existing FastAPI, SQLAlchemy, Alembic, frontend, configuration,
   CORS, and security conventions before changing code.
2. Add durable `User` identity with normalized unique email, secure password
   hash, `ADMIN`/`USER` role, `ACTIVE`/`DISABLED` status, and timestamps.
3. Keep immutable `user_id` as the future quota/reservation foreign-key key;
   email remains changeable identity data, not the durable relationship key.
4. Use short-lived configurable access tokens and separately configurable
   refresh-session lifetimes. Store only hashed refresh tokens server-side.
5. Rotate refresh tokens on successful refresh and revoke the previous session
   token. Check revocation server-side on every refresh.
6. Add an idempotent local admin-bootstrap command. Existing admin email must
   stop safely without changing its password or role.
7. Add reusable `get_current_user`, `require_active_user`, and `require_admin`
   dependencies.
8. Add login, logout, refresh, current-user, and minimal admin user-management
   APIs.
9. Protect operational telemetry as admin-only and document staged protection
   for Search Volume execution/preview routes.
10. Add minimal frontend login, auth restoration, logout, and authorization
    handling. Do not build the browser extension in this phase.

## Authentication decision

Use short-lived access tokens plus revocable refresh sessions. This fits the
FastAPI API and future extension clients better than assuming a shared-domain
cookie, while keeping access-token exposure short. Web and extension storage
expectations must be documented separately; long-lived refresh tokens must not
be placed in ordinary browser `localStorage` by default.

Access-token and refresh-session lifetimes are configuration values, not
business-logic constants. Tokens contain only minimal identity claims and no
provider credentials, quota values, or password data.

## Data model

`User`:

- immutable stable ID;
- normalized unique email;
- display name if needed;
- password hash only;
- role and status;
- created/updated/last-login timestamps.

`UserSession`:

- session ID;
- `user_id` foreign key;
- refresh-token hash;
- created/expiry/revoked/last-used timestamps;
- optional `WEB`/`EXTENSION` client type.

No `UserProviderQuota`, bonus, reservation, subscription, billing, or payment
tables are added here.

## API surface

```text
POST  /api/v1/auth/login
POST  /api/v1/auth/logout
POST  /api/v1/auth/refresh
GET   /api/v1/auth/me
GET   /api/v1/admin/users
POST  /api/v1/admin/users
GET   /api/v1/admin/users/{user_id}
PATCH /api/v1/admin/users/{user_id}
```

The last active administrator cannot be disabled or demoted. Password reset,
if included, invalidates existing refresh sessions according to the chosen
security policy.

## Route rollout

Authentication is introduced without silently breaking the current frontend.
The implementation must explicitly classify current routes as public,
authenticated, or admin-only. Provider telemetry should be admin-only. Search
Volume execution and batch preview should be staged to authenticated access
once frontend login integration is ready; any temporary public status must be
documented.

## Security requirements

- Argon2id or the existing approved password library;
- generic login failure responses;
- disabled users rejected;
- expired and revoked sessions rejected;
- refresh rotation and server-side revocation checks;
- authentication endpoint abuse protection separate from Google rate limiting;
- secrets loaded from environment and never logged;
- CORS and cookie/token handling reviewed;
- no default credentials.

## Validation boundary

All tests are local and mocked. Required provider counts remain:

```text
Google Ads: 0
Google customer metadata: 0
FX: 0
SERP/Moz/Ahrefs/DataForSEO: 0
Other external providers: 0
```

The implementation must regress-test the existing Google access gate,
ProviderCall telemetry, CustomerRateLimiter, rolling budget,
`UNKNOWN_UNVERIFIED`, `BUDGET_EXCEEDED`, preview, and provider telemetry.

## Required security regressions

- refresh rotation invalidates the previous token;
- revoked sessions cannot refresh;
- role changes apply to newly issued access tokens;
- email changes preserve `user_id`;
- last active admin cannot be removed;
- password reset invalidates sessions if enabled;
- disabled users cannot use previously issued access tokens;
- admin endpoints reject ordinary users;
- unauthenticated `/me` returns `401`.

## Migration and handoff

Add isolated Alembic migration(s) for users and sessions, with unique email
constraint, necessary indexes, foreign keys, and upgrade/downgrade validation.
Audit future ownership attachment points for batches/runs but do not assign
anonymous historical records or add quota models.

This phase remains uncommitted until implementation, tests, static checks, and
route/security review pass. The next phase after review and commit is
per-user provider quotas and reservations.

## Implementation status

Implemented locally: user/session models, local authentication APIs, password
security, rotating refresh sessions, admin management, bootstrap command,
last-admin protection, authentication attempt limiting, frontend login/client,
admin-only provider telemetry, and isolated migration validation. Search Volume
execution protection remains staged for frontend rollout. The phase is
uncommitted and awaiting final review.
