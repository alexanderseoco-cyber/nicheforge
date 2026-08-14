from dotenv import dotenv_values
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

env = dotenv_values(r"E:\programming\Local SEO Niche Validation Tool\.env")

creds = Credentials(
    token=None,
    refresh_token=env.get("GOOGLE_ADS_REFRESH_TOKEN"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=env.get("GOOGLE_ADS_CLIENT_ID"),
    client_secret=env.get("GOOGLE_ADS_CLIENT_SECRET"),
    scopes=["https://www.googleapis.com/auth/adwords"],
)

try:
    creds.refresh(Request())
    print("OAUTH_REFRESH_OK")
    print("ACCESS_TOKEN_RECEIVED:", bool(creds.token))
except Exception as exc:
    print("OAUTH_REFRESH_FAILED")
    print("ERROR_TYPE:", type(exc).__name__)
    print("SAFE_ERROR:", str(exc)[:800])
