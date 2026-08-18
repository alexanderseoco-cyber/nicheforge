from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ProviderCache


def upsert_provider_cache(
    db: Session,
    *,
    cache_key: str,
    provider: str,
    operation: str,
    evidence_type: str,
    evidence_id: str,
    fetched_at: datetime,
    fresh_until: datetime | None,
    status: str = "usable",
    last_error: str | None = None,
) -> ProviderCache:
    """Maintain the current reusable pointer without rewriting evidence history."""
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == cache_key))
    if cache is None:
        cache = ProviderCache(cache_key=cache_key)
        db.add(cache)
    cache.provider = provider
    cache.operation = operation
    cache.evidence_type = evidence_type
    cache.evidence_id = evidence_id
    cache.status = status
    cache.fetched_at = fetched_at
    cache.fresh_until = fresh_until
    cache.last_error = last_error
    db.flush()
    return cache
