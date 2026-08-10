from __future__ import annotations

import hashlib
import json
from typing import Any


def provider_cache_key(provider: str, evidence_type: str, **dimensions: Any) -> str:
    payload = {
        "provider": provider.strip().lower(),
        "evidence_type": evidence_type.strip().lower(),
        "dimensions": dimensions,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evidence_is_fresh(fresh_until, now=None) -> bool:
    from datetime import datetime, timezone
    now = now or datetime.now(timezone.utc)
    if fresh_until is None:
        return False
    if fresh_until.tzinfo is None:
        return fresh_until >= now.replace(tzinfo=None)
    return fresh_until >= now
