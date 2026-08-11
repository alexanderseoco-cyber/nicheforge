"""Import previously observed proxy evidence into a calibration database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ProxyAuthorityEvidence, ProviderCache
from app.services.cache_keys import provider_cache_key


def import_ahrefs_evidence(source_db: Session, target_db: Session, source_database: str) -> list[ProxyAuthorityEvidence]:
    """Copy Ahrefs observations without creating a provider-call record.

    The source session is read-only by convention. Imported rows retain their
    observed timestamp/value and gain explicit source-database provenance.
    """
    imported: list[ProxyAuthorityEvidence] = []
    for source in source_db.scalars(select(ProxyAuthorityEvidence).order_by(ProxyAuthorityEvidence.fetched_at)).all():
        existing = target_db.scalar(select(ProxyAuthorityEvidence).where(ProxyAuthorityEvidence.root_domain == source.root_domain).order_by(ProxyAuthorityEvidence.fetched_at.desc()))
        if existing:
            continue
        evidence = ProxyAuthorityEvidence(
            id=source.id,
            target_url=source.target_url,
            root_domain=source.root_domain,
            provider=source.provider,
            metric=source.metric,
            domain_rating=source.domain_rating,
            source_kind="imported_calibration",
            raw_payload=source.raw_payload or {},
            request_metadata={**(source.request_metadata or {}), "imported_from_database": source_database, "original_source_kind": source.source_kind, "original_evidence_id": source.id},
            fetched_at=source.fetched_at,
            fresh_until=source.fresh_until,
        )
        target_db.add(evidence)
        target_db.flush()
        key = provider_cache_key("ahrefs", "domain_rating", root_domain=source.root_domain)
        cache = target_db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
        if cache:
            cache.evidence_id = evidence.id; cache.status = "usable"; cache.fetched_at = evidence.fetched_at; cache.fresh_until = evidence.fresh_until
        else:
            target_db.add(ProviderCache(cache_key=key, provider="ahrefs", operation="domain_rating_free", evidence_type="proxy_authority", evidence_id=evidence.id, status="usable", fetched_at=evidence.fetched_at, fresh_until=evidence.fresh_until))
        imported.append(evidence)
    target_db.commit()
    return imported
