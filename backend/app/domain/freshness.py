from enum import StrEnum


class FreshnessPolicy(StrEnum):
    REUSE_FRESH_ONLY = "REUSE_FRESH_ONLY"
    ALLOW_STALE_WITH_WARNING = "ALLOW_STALE_WITH_WARNING"
    FORCE_REFRESH = "FORCE_REFRESH"


def can_reuse(policy: FreshnessPolicy | str, is_fresh: bool) -> tuple[bool, bool]:
    policy = FreshnessPolicy(policy)
    if policy == FreshnessPolicy.FORCE_REFRESH:
        return False, False
    if is_fresh:
        return True, False
    return (policy == FreshnessPolicy.ALLOW_STALE_WITH_WARNING, True)
