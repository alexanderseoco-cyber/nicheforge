import pytest
from app.services.currency_normalization import ExchangeRateApiProvider, normalize_to_usd


class Response:
    def raise_for_status(self): pass
    def json(self): return {"rates": {"USD": 0.0036}, "time_last_update_utc": "Fri, 14 Aug 2026 00:00:00 +0000"}


class Client:
    def __init__(self): self.calls = 0
    async def get(self, url): self.calls += 1; return Response()


@pytest.mark.asyncio
async def test_fx_provider_caches_one_daily_pair():
    client = Client(); provider = ExchangeRateApiProvider(client=client)
    first = await provider.get_rate("PKR", "USD", "2026-08-14")
    second = await provider.get_rate("PKR", "USD", "2026-08-14")
    assert first.rate == second.rate == 0.0036
    assert client.calls == 1 and provider.network_calls == 1
    value, fx = normalize_to_usd(744.940438, "PKR", rate=first)
    assert round(value, 8) == round(744.940438 * 0.0036, 8)
    assert fx.source == "exchangerate_api_open"
