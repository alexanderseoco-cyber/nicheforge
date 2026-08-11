import asyncio

from app.providers.ahrefs import AhrefsDomainRatingProvider
from app.providers.contracts import AuthorityTarget
from app.services.proxy_authority import evaluate_proxy


def test_ahrefs_proxy_contract_mapping_and_identity(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"domain_rating": {"domain_rating": 8.5, "license": "https://ahrefs.com/legal/domain-rating-license", "warning": None}}

    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, headers, params):
            assert url.endswith("/v3/public/domain-rating-free")
            assert headers["Authorization"] == "Bearer test-key"
            assert params == {"target": "example.com"}
            return Response()

    monkeypatch.setattr("app.providers.ahrefs.httpx.AsyncClient", lambda timeout: Client())
    result = asyncio.run(AhrefsDomainRatingProvider("test-key", enabled=True, live_approved=True).fetch([AuthorityTarget("https://www.example.com/a", "example.com")]))[0]
    assert result.provider == "ahrefs"
    assert result.metric == "domain_rating"
    assert result.domain_rating == 8.5
    assert result.raw["domain_rating"]["license"]


def test_proxy_classifications_are_not_moz_decisions():
    strong = evaluate_proxy([5, 8, 10, 12, 14], threshold=14)
    review = evaluate_proxy([5, 8, 20, 18, None], threshold=14)
    rejected = evaluate_proxy([40, 50, 60, 70, 80], threshold=14)
    incomplete = evaluate_proxy([5, None, None, None, None], threshold=14)
    assert strong.classification == "PROXY_STRONG_CANDIDATE"
    assert review.classification == "PROXY_REVIEW"
    assert rejected.classification == "PROXY_REJECTED_HIGH_CONFIDENCE"
    assert incomplete.classification == "PROXY_REVIEW"
    assert all(not item.classification in {"PASS", "IDEAL", "PRIMARY_REJECTED"} for item in (strong, review, rejected, incomplete))


def test_proxy_review_preserves_false_negative_safety():
    result = evaluate_proxy([20, 19, 18, 17, 16, None], threshold=14)
    assert result.classification == "PROXY_REVIEW"
    assert result.why_not_rejected
    assert result.recommended_action == "MANUAL_MOZ_VALIDATION"


def test_ahrefs_network_is_disabled_by_default_before_transport(monkeypatch):
    class NeverClient:
        def __init__(self, *args, **kwargs): raise AssertionError("transport must not be constructed")
    monkeypatch.setattr("app.providers.ahrefs.httpx.AsyncClient", NeverClient)
    provider = AhrefsDomainRatingProvider("test-key")
    try:
        asyncio.run(provider.fetch([AuthorityTarget("https://example.com", "example.com")]))
    except RuntimeError as exc:
        assert "AHREFS_PROXY_ENABLED" in str(exc)
    else:
        raise AssertionError("disabled Ahrefs execution was not blocked")


def test_ahrefs_missing_key_is_rejected_before_transport():
    try:
        AhrefsDomainRatingProvider("")
    except ValueError as exc:
        assert "API key" in str(exc)
    else:
        raise AssertionError("missing Ahrefs key was not rejected")


def test_ahrefs_requires_explicit_live_approval():
    provider = AhrefsDomainRatingProvider("test-key", enabled=True, live_approved=False)
    try:
        provider.validate_live_execution()
    except RuntimeError as exc:
        assert "AHREFS_LIVE_APPROVED" in str(exc)
    else:
        raise AssertionError("unapproved Ahrefs execution was not blocked")


def test_ahrefs_approved_boundary_validates_without_network():
    AhrefsDomainRatingProvider("test-key", enabled=True, live_approved=True).validate_live_execution()
