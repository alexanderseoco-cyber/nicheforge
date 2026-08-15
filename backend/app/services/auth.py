"""Local authentication primitives; no external identity provider required."""
from __future__ import annotations

import base64, hashlib, hmac, json, secrets
from datetime import datetime, timedelta

PASSWORD_ROUNDS = 600_000


def normalize_email(email: str) -> str:
    value = email.strip().casefold()
    if not value or "@" not in value or value.startswith("@") or value.endswith("@"):
        raise ValueError("A valid email is required")
    return value


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ROUNDS)
    return f"pbkdf2_sha256${PASSWORD_ROUNDS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(rounds))
        return hmac.compare_digest(base64.urlsafe_b64encode(actual).decode(), expected)
    except (ValueError, TypeError):
        return False


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def issue_access_token(user_id: str, role: str, secret: str, lifetime_seconds: int) -> str:
    now = datetime.utcnow()
    payload = {"sub": user_id, "role": role, "iat": int(now.timestamp()), "exp": int((now + timedelta(seconds=lifetime_seconds)).timestamp()), "token_type": "access"}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())}"


def decode_access_token(token: str, secret: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected): raise ValueError("invalid token")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if payload.get("token_type") != "access" or int(payload["exp"]) <= int(datetime.utcnow().timestamp()): raise ValueError("expired token")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise ValueError("invalid access token")


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
