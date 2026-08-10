# NicheForge

Read `PROJECT.md`, then `docs/PROJECT_BLUEPRINT.md` before changing architecture.

## Run backend locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Defaults use deterministic mock providers, so the full Phase-1 funnel can be tested without paid credentials.

## Minimal flow

1. POST `/api/v1/cities` a few test cities.
2. POST `/api/v1/projects`.
3. POST `/api/v1/projects/{id}/candidates/generate` with niches.
4. POST `/api/v1/projects/{id}/run`.
5. GET `/api/v1/projects/{id}/candidates`.

To use DataForSEO for SV/SERP, copy `.env.example` to `.env`, set credentials and provider names to `dataforseo`.

Moz is intentionally configured through an adapter with environment-provided endpoint/path. Confirm the authorized current Moz API contract for the account before enabling `NICHEFORGE_AUTHORITY_PROVIDER=moz`.
