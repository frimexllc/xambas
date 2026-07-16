from datetime import datetime, timedelta, timezone
import hashlib
import secrets


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_otp_code(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def build_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_expiration(minutes: int = 10) -> datetime:
    return utc_now() + timedelta(minutes=minutes)


def build_session_expiration(hours: int = 24) -> datetime:
    return utc_now() + timedelta(hours=hours)
