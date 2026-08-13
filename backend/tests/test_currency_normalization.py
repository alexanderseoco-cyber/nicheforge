from app.services.currency_normalization import FxRate, normalize_to_usd


def test_pk_currency_preserved_and_usd_is_derived_with_provenance():
    value, fx = normalize_to_usd(744.940438, "PKR", rate=FxRate("PKR", "USD", 0.0036, "2026-08-14", "mock_fx"))
    assert value == 2.6817855768
    assert fx.source_currency == "PKR" and fx.target_currency == "USD"


def test_usd_identity_requires_no_fx_provider():
    value, fx = normalize_to_usd(1.75, "USD", rate=None)
    assert value == 1.75 and fx.rate == 1.0 and fx.source == "identity"


def test_missing_currency_or_rate_is_unavailable():
    assert normalize_to_usd(10, None, rate=None) == (None, None)
    assert normalize_to_usd(10, "PKR", rate=None) == (None, None)
