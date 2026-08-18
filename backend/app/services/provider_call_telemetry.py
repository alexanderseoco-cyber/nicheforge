"""Best-effort ProviderCall persistence and shared telemetry vocabulary."""
from __future__ import annotations

import logging
from collections.abc import Callable

from app.models.entities import ProviderCall

logger = logging.getLogger(__name__)

COST_CONFIDENCE = frozenset({"ACTUAL", "PROVIDER_REPORTED", "ESTIMATED", "UNKNOWN", "NOT_APPLICABLE"})
OPERATION_CATEGORIES = frozenset({"PROVIDER_ACQUISITION", "CACHE_REUSE", "PARENT_EVIDENCE_REUSE", "SUMMARY"})


def safe_add_provider_call(db, provider_call: ProviderCall) -> ProviderCall | None:
    """Persist telemetry in a savepoint; never propagate telemetry failures."""
    try:
        with db.begin_nested():
            db.add(provider_call)
            db.flush()
        return provider_call
    except Exception as exc:  # telemetry is observational by contract
        logger.warning("provider_call_telemetry_write_failed: %s", type(exc).__name__)
        return None


def safe_create_provider_call(db, factory: Callable[[], ProviderCall]) -> ProviderCall | None:
    """Construct and persist a telemetry row inside the same savepoint."""
    try:
        with db.begin_nested():
            provider_call = factory()
            db.add(provider_call)
            db.flush()
        return provider_call
    except Exception as exc:
        logger.warning("provider_call_telemetry_write_failed: %s", type(exc).__name__)
        return None


def safe_update_provider_call(db, provider_call: ProviderCall | None, **values) -> bool:
    """Best-effort update of an already-created telemetry row."""
    if provider_call is None:
        return False
    try:
        with db.begin_nested():
            for name, value in values.items():
                setattr(provider_call, name, value)
            db.flush()
        return True
    except Exception as exc:  # telemetry must not poison provider execution
        logger.warning("provider_call_telemetry_update_failed: %s", type(exc).__name__)
        return False
