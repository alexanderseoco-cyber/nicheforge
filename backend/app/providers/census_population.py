from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
import csv
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class CensusPopulationResult:
    place_name: str
    state_fips: str
    place_fips: str
    geoid: str
    population: int
    vintage: str
    dataset: str
    raw: dict[str, Any]


def redact_census_url(url: str) -> str:
    parts = urlsplit(url)
    query = [(k, "[REDACTED]") if k.lower() == "key" else (k, v) for k, v in __import__("urllib.parse", fromlist=["parse_qsl"]).parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class CensusPopulationProvider:
    dataset = "data/2023/pep/population"
    vintage = "2023"

    def __init__(self, api_key: str | None, enabled: bool, base_url: str = "https://api.census.gov"):
        self.api_key = api_key
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")

    def validate_live_execution(self) -> None:
        if not self.enabled:
            raise RuntimeError("CENSUS_API_ENABLED must be true before Census network execution")
        if not self.api_key:
            raise RuntimeError("CENSUS_API_KEY is required before Census network execution")

    async def resolve_places(self, state_fips: str) -> list[CensusPopulationResult]:
        self.validate_live_execution()
        params = {"get": "NAME,POP_2023", "for": "place:*", "in": f"state:{state_fips}", "key": self.api_key}
        url = f"{self.base_url}/{self.dataset}?{urlencode(params)}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            raise RuntimeError(f"Census request failed at {redact_census_url(url)}") from exc
        header, *rows = payload
        result = []
        for row in rows:
            item = dict(zip(header, row))
            result.append(CensusPopulationResult(item["NAME"], item["state"], item["place"], f"1600000US{item['state']}{item['place']}", int(item["POP_2023"]), self.vintage, self.dataset, {"NAME": item["NAME"], "POP_2023": item["POP_2023"], "state": item["state"], "place": item["place"]}))
        return result


class CensusSubEst2025Provider:
    dataset = "SUB-EST2025"
    vintage = "2025"

    def __init__(self, path: str):
        self.path = Path(path)
        self.file_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def resolve(self, city: str, state_fips: str) -> CensusPopulationResult | None:
        normalized = " ".join(city.lower().replace(".", "").split())
        matches = []
        with self.path.open(encoding="latin-1", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("SUMLEV") != "162" or row.get("STATE") != state_fips or not row.get("PLACE"):
                    continue
                name = row.get("NAME", "").lower()
                name = __import__("re").sub(r"\s+(city|town|village|borough)$", "", name)
                if " ".join(name.replace(".", "").split()) == normalized:
                    matches.append(row)
        if len(matches) != 1:
            return None
        row = matches[0]
        return CensusPopulationResult(row["NAME"], row["STATE"], row["PLACE"], f"1600000US{row['STATE']}{row['PLACE']}", int(row["POPESTIMATE2025"]), self.vintage, self.dataset, {"SUMLEV": row["SUMLEV"], "STATE": row["STATE"], "PLACE": row["PLACE"], "NAME": row["NAME"], "POPESTIMATE2025": row["POPESTIMATE2025"], "source_file_hash": self.file_hash})
