import asyncio
from app.providers.dataforseo import DataForSEOSerpProvider
from app.providers.contracts import SerpRequest
from app.providers.runtime_config import ProviderMode


class Client:
    def __init__(self): self.payload = None
    async def post(self, path, payload):
        self.payload = payload
        return {"tasks": [{"status_code": 20000, "result": [{"items": [{"type": "organic", "rank_absolute": 1, "title": "x", "url": "https://example.com"}]}]}]}


def test_general_serp_uses_country_location_code_without_city_resolver():
    client = Client()
    provider = DataForSEOSerpProvider("x", "y", ProviderMode.TRIAL, location_resolver=None)
    provider.client = client
    asyncio.run(provider.fetch([SerpRequest("fancy text generator", "United States", "en", 10, "US", 2840)]))
    assert client.payload[0]["location_code"] == 2840
    assert "location_name" not in client.payload[0]
