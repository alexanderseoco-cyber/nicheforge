from __future__ import annotations

import hashlib
import unicodedata

from app.services.normalization import normalize_keyword


def canonical_identity(service_term: str, geographic_id: str, language_code: str = "en", country_code: str = "US") -> str:
    """Build identity from canonical fields, never display text."""
    service = unicodedata.normalize("NFKC", normalize_keyword(service_term))
    geo = unicodedata.normalize("NFKC", geographic_id.strip().lower())
    language = language_code.strip().lower()
    country = country_code.strip().upper()
    if not service or not geo or not language or not country:
        raise ValueError("service, geographic identity, language, and country are required")
    return "|".join((service, geo, language, country))


def identity_key(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
