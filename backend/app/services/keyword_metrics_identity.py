from __future__ import annotations

import hashlib
import json


METRIC_VERSION = "keyword_metrics_v1"


def normalize_metric_keyword(keyword: str) -> str:
    return " ".join(keyword.strip().casefold().split())


def keyword_metric_cache_key(*, keyword: str, location_name: str | None,
                             location_target: dict | None, language_code: str,
                             country_code: str, provider: str,
                             targeting_mode: str = "keyword_and_geo",
                             metric_version: str = METRIC_VERSION) -> str:
    identity = {
        "keyword": normalize_metric_keyword(keyword),
        "location_name": location_name.strip().casefold() if location_name else None,
        "location_target": location_target or {},
        "language_code": language_code.casefold(),
        "country_code": country_code.upper(),
        "provider": provider.casefold(),
        "targeting_mode": targeting_mode.casefold(),
        "metric_version": metric_version,
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return "keyword_metrics:" + hashlib.sha256(payload.encode()).hexdigest()
