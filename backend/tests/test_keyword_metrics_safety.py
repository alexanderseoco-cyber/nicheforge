import pytest

from app.providers.keyword_metrics_safety import KeywordMetricsSafetyConfig, redact_secret_text


def test_missing_credentials_blocks_before_transport():
    with pytest.raises(PermissionError, match="credentials"):
        KeywordMetricsSafetyConfig("google_ads", enabled=True, live_approved=True, credentials_configured=False).validate(1, 0)


def test_budget_and_batch_rate_guards_reject():
    config = KeywordMetricsSafetyConfig("google_ads", enabled=True, live_approved=True, credentials_configured=True, max_batch_size=2, budget=0.01)
    with pytest.raises(ValueError, match="batch"):
        config.validate(3, 0)
    with pytest.raises(ValueError, match="cost"):
        config.validate(1, 0.02)
    with pytest.raises(ValueError, match="rate"):
        KeywordMetricsSafetyConfig("mock", requests_per_second=0).validate()


def test_secret_safe_errors_and_logs():
    secret = "super-secret-token"
    safe = redact_secret_text(f"request failed token={secret} key={secret}", [secret])
    assert secret not in safe
    assert "[REDACTED]" in safe


def test_google_batch_boundary_accepts_10000_and_rejects_10001():
    config=KeywordMetricsSafetyConfig("google_ads", enabled=True, live_approved=True, credentials_configured=True, max_batch_size=10000)
    config.validate(10000, 0)
    with pytest.raises(ValueError, match="batch"):
        config.validate(10001, 0)
