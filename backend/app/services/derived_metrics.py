"""Versioned, provider-independent commercial opportunity calculations."""
from __future__ import annotations
from dataclasses import dataclass

CTR_MODEL_V1 = {1: 0.28, 3: 0.10, 5: 0.05}

@dataclass(frozen=True)
class DerivedKeywordMetrics:
    commercial_search_value: float | None
    projected: dict
    ctr_model_version: str
    calculation_version: str = "commercial_metrics_v1"

def calculate_derived_metrics(search_volume: int | None, usd_cpc: float | None, *, ctr_model: dict[int, float] | None = None, ctr_model_version: str = "v1") -> DerivedKeywordMetrics:
    model = ctr_model or CTR_MODEL_V1
    if search_volume is None:
        return DerivedKeywordMetrics(None, {str(position): {"ctr": ctr, "clicks": None, "traffic_value": None} for position, ctr in model.items()}, ctr_model_version)
    commercial = None if usd_cpc is None else search_volume * usd_cpc
    projected = {}
    for position, ctr in model.items():
        clicks = search_volume * ctr
        projected[str(position)] = {"ctr": ctr, "clicks": clicks, "traffic_value": None if usd_cpc is None else clicks * usd_cpc}
    return DerivedKeywordMetrics(commercial, projected, ctr_model_version)
