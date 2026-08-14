"""Run exactly one authorized local Search Volume request.

This uses the same FastAPI contract as the frontend and performs no retries,
fallbacks, or additional provider calls.
"""
from __future__ import annotations

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


payload = {
    "keywords": ["dental clinic"],
    "target": {
        "location_name": None,
        "location_target": {"country_code": "US"},
        "language_code": "en",
        "country_code": "US",
    },
    "provider": "google_ads",
}

request = Request(
    "http://127.0.0.1:8000/api/v1/keyword-metrics/research",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urlopen(request, timeout=120) as response:
        body = response.read().decode()
        print(f"HTTP_STATUS: {response.status}")
        print(body)
except HTTPError as exc:
    print(f"HTTP_STATUS: {exc.code}")
    print(exc.read().decode(errors="replace"))
except URLError as exc:
    print("NETWORK_ERROR: backend_unreachable")
    print(f"SAFE_MESSAGE: {exc.reason}")
