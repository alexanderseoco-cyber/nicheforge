from dataclasses import dataclass
from datetime import datetime, timezone
import re

@dataclass(frozen=True)
class ResolvedLocation:
    name: str
    code: int
    country_code: str
    provider: str
    resolved_at: datetime

class LocationResolutionError(ValueError):
    pass

class DataForSEOLocationResolver:
    def __init__(self, client):
        self.client = client
        self._cache = {}

    @staticmethod
    def _key(city: str, state: str, country: str) -> tuple[str, str, str]:
        compact = lambda value: re.sub(r"\s*,\s*", ",", value.strip().casefold())
        return compact(city), compact(state), compact(country)

    def cache_verified(self, location: ResolvedLocation, city: str, state: str,
                       country: str = "United States") -> None:
        """Cache a record already obtained from the official provider dataset."""
        self._cache[self._key(city, state, country)] = location

    async def resolve(self, city: str, state: str, country: str = "United States") -> ResolvedLocation:
        key = self._key(city, state, country)
        if key in self._cache:
            return self._cache[key]
        data = await self.client.get("/v3/serp/google/locations")
        tasks = data.get("tasks") or []
        rows = []
        if tasks:
            result = (tasks[0].get("result") or [])
            rows = result.get("locations", []) if isinstance(result, dict) else result
        if not rows:
            result = data.get("result") or data.get("locations") or []
            rows = result.get("locations", []) if isinstance(result, dict) else result
        wanted = self._key(city, state, country)
        def normalized_name(value: str) -> tuple[str, str, str]:
            parts = [part.strip() for part in re.split(r",", value)]
            return self._key(*(parts + [""] * 3)[:3])
        matches = [r for r in rows if normalized_name(str(r.get("location_name", ""))) == wanted]
        if len(matches) != 1:
            available = [str(r.get("location_name", "")) for r in rows[:10] if isinstance(r, dict)]
            raise LocationResolutionError(f"location ambiguous or not found; available={available}")
        row = matches[0]
        if row.get("location_code") is None:
            raise LocationResolutionError("provider location code missing")
        result = ResolvedLocation(row["location_name"], int(row["location_code"]), "US", "dataforseo", datetime.now(timezone.utc))
        self._cache[key] = result
        return result
