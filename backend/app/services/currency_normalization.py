"""Provider-neutral, provenance-preserving monetary normalization."""
from dataclasses import dataclass
from datetime import date
from email.utils import parsedate_to_datetime
import httpx


@dataclass(frozen=True)
class FxRate:
    source_currency: str
    target_currency: str
    rate: float
    rate_date: str
    source: str


class CurrencyRateProvider:
    def get_rate(self, from_currency: str, to_currency: str, date: str | None = None) -> FxRate | None:
        raise NotImplementedError


class ExchangeRateApiProvider(CurrencyRateProvider):
    """ExchangeRate-API open-access adapter with one-rate-per-day caching."""
    provider_name = "exchangerate_api_open"
    base_url = "https://open.er-api.com/v6/latest"

    def __init__(self, *, client=None, cache=None):
        self.client = client or httpx.AsyncClient(timeout=15)
        self.cache = cache if cache is not None else {}
        self.network_calls = 0

    async def get_rate(self, from_currency: str, to_currency: str, date: str | None = None) -> FxRate | None:
        source, target = from_currency.upper(), to_currency.upper()
        day = date or __import__("datetime").date.today().isoformat()
        key = (source, target, day, self.provider_name)
        if key in self.cache:
            return self.cache[key]
        if source == target:
            rate = FxRate(source, target, 1.0, day, "identity")
            self.cache[key] = rate
            return rate
        self.network_calls += 1
        response = await self.client.get(f"{self.base_url}/{source}")
        response.raise_for_status()
        payload = response.json()
        value = (payload.get("rates") or {}).get(target)
        if value is None:
            return None
        raw_date = str(payload.get("time_last_update_utc") or "")
        try:
            rate_date = parsedate_to_datetime(raw_date).date().isoformat()
        except (TypeError, ValueError, IndexError):
            rate_date = day
        rate = FxRate(source, target, float(value), rate_date, self.provider_name)
        self.cache[key] = rate
        return rate


def normalize_to_usd(value: float | None, source_currency: str | None, *, rate: FxRate | None) -> tuple[float | None, FxRate | None]:
    if value is None or not source_currency:
        return None, None
    if source_currency.upper() == "USD":
        return value, FxRate("USD", "USD", 1.0, "provider_metadata", "identity")
    if rate is None:
        return None, None
    return value * rate.rate, rate
