from dataclasses import dataclass
from datetime import datetime, timezone
import re

US_STATE_NAMES = {
    "alabama":"AL", "alaska":"AK", "arizona":"AZ", "arkansas":"AR", "california":"CA",
    "colorado":"CO", "connecticut":"CT", "delaware":"DE", "florida":"FL", "georgia":"GA",
    "hawaii":"HI", "idaho":"ID", "illinois":"IL", "indiana":"IN", "iowa":"IA",
    "kansas":"KS", "kentucky":"KY", "louisiana":"LA", "maine":"ME", "maryland":"MD",
    "massachusetts":"MA", "michigan":"MI", "minnesota":"MN", "mississippi":"MS",
    "missouri":"MO", "montana":"MT", "nebraska":"NE", "nevada":"NV", "new hampshire":"NH",
    "new jersey":"NJ", "new mexico":"NM", "new york":"NY", "north carolina":"NC",
    "north dakota":"ND", "ohio":"OH", "oklahoma":"OK", "oregon":"OR", "pennsylvania":"PA",
    "rhode island":"RI", "south carolina":"SC", "south dakota":"SD", "tennessee":"TN",
    "texas":"TX", "utah":"UT", "vermont":"VT", "virginia":"VA", "washington":"WA",
    "west virginia":"WV", "wisconsin":"WI", "wyoming":"WY", "district of columbia":"DC",
}

@dataclass(frozen=True)
class ResolvedLocation:
    name: str
    code: int
    country_code: str
    provider: str
    resolved_at: datetime
    location_type: str = "City"
    source_endpoint: str = "/v3/serp/google/locations/us"

class LocationResolutionError(ValueError):
    pass

class DataForSEOLocationResolver:
    def __init__(self, client):
        self.client = client
        self._cache = {}

    @staticmethod
    def _key(city: str, state: str, country: str) -> tuple[str, str, str]:
        compact = lambda value: re.sub(r"\s*,\s*", ",", value.strip().casefold())
        state_key = compact(state)
        state_key = US_STATE_NAMES.get(state_key, state_key).upper()
        return compact(city), state_key, compact(country)

    def cache_verified(self, location: ResolvedLocation, city: str, state: str,
                       country: str = "United States") -> None:
        """Cache a record already obtained from the official provider dataset."""
        self._cache[self._key(city, state, country)] = location

    async def resolve(self, city: str, state: str, country: str = "United States") -> ResolvedLocation:
        key = self._key(city, state, country)
        if key in self._cache:
            return self._cache[key]
        source_endpoint = "/v3/serp/google/locations/us"
        data = await self.client.get(source_endpoint)
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
        def is_city(r: dict) -> bool:
            location_type = str(r.get("location_type", "City")).casefold()
            return location_type in {"city", "municipality", "town"}

        def is_us(r: dict) -> bool:
            requested_country = "US" if country.casefold() in {"us", "united states", "usa"} else country.upper()
            return str(r.get("country_iso_code", requested_country)).upper() == requested_country

        matches = [r for r in rows if is_us(r) and is_city(r)
                   and normalized_name(str(r.get("location_name", ""))) == wanted]
        if len(matches) != 1:
            available = [str(r.get("location_name", "")) for r in rows[:10] if isinstance(r, dict)]
            raise LocationResolutionError(f"location ambiguous or not found; available={available}")
        row = matches[0]
        if row.get("location_code") is None:
            raise LocationResolutionError("provider location code missing")
        result = ResolvedLocation(row["location_name"], int(row["location_code"]), country.upper(), "dataforseo", datetime.now(timezone.utc), str(row.get("location_type") or "City"), source_endpoint)
        self._cache[key] = result
        return result
