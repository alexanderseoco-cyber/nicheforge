"""User-run, OAuth-only Google Ads runtime diagnostic.

This intentionally performs no Google Ads RPC. It reports only sanitized
configuration and construction stages.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.core.config import get_settings


def fingerprint(value: str | None) -> str:
    return hashlib.sha256((value or "").encode()).hexdigest()[:16]


def safe_error(exc: BaseException) -> tuple[str, str]:
    return type(exc).__name__, str(exc).split("\n", 1)[0][:240]


def main() -> int:
    settings = get_settings()
    print("SETTINGS_LOAD: PASS")
    print(f"INTERPRETER: {sys.executable}")
    print(f"WORKING_DIRECTORY: {Path.cwd()}")
    print(f"SETTINGS_ENV_FILE: {Path.cwd().parent / '.env'}")
    print(f"TOKEN_PRESENT: {bool(settings.google_ads_refresh_token)}")
    print(f"TOKEN_FINGERPRINT: {fingerprint(settings.google_ads_refresh_token)}")
    print(f"CLIENT_ID_PRESENT: {bool(settings.google_ads_client_id)}")
    print(f"GOOGLE_FLAGS: {settings.google_ads_enabled}/{settings.google_ads_live_approved}")

    credentials = Credentials(
        token=None,
        refresh_token=settings.google_ads_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
        scopes=["https://www.googleapis.com/auth/adwords"],
    )
    try:
        credentials.refresh(Request())
        print("OAUTH_REFRESH: PASS")
    except Exception as exc:  # sanitized diagnostic only
        kind, message = safe_error(exc)
        print("OAUTH_REFRESH: FAIL")
        print(f"STAGE: oauth_refresh\nEXCEPTION_TYPE: {kind}\nSAFE_CATEGORY: credential_refresh_transport\nSAFE_MESSAGE: {message}")
        print("GOOGLE_ADS_CLIENT: NOT_RUN\nKEYWORD_PLAN_SERVICE: NOT_RUN\nGOOGLE_ADS_RPC: 0")
        return 1

    try:
        client = GoogleAdsClient.load_from_dict({
            "developer_token": settings.google_ads_developer_token,
            "client_id": settings.google_ads_client_id,
            "client_secret": settings.google_ads_client_secret,
            "refresh_token": settings.google_ads_refresh_token,
            "login_customer_id": settings.google_ads_login_customer_id,
            "use_proto_plus": True,
        })
        print("GOOGLE_ADS_CLIENT: PASS")
    except Exception as exc:  # sanitized diagnostic only
        kind, message = safe_error(exc)
        print(f"GOOGLE_ADS_CLIENT: FAIL\nSTAGE: client_construction\nEXCEPTION_TYPE: {kind}\nSAFE_CATEGORY: client_or_endpoint\nSAFE_MESSAGE: {message}\nKEYWORD_PLAN_SERVICE: NOT_RUN\nGOOGLE_ADS_RPC: 0")
        return 1

    try:
        client.get_service("KeywordPlanIdeaService", version="v25")
        print("KEYWORD_PLAN_SERVICE: PASS")
    except Exception as exc:  # sanitized diagnostic only
        kind, message = safe_error(exc)
        print(f"KEYWORD_PLAN_SERVICE: FAIL\nSTAGE: service_construction\nEXCEPTION_TYPE: {kind}\nSAFE_CATEGORY: client_or_endpoint\nSAFE_MESSAGE: {message}")
        print("GOOGLE_ADS_RPC: 0")
        return 1

    print("GOOGLE_ADS_RPC: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
