import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from .config import get_settings

settings = get_settings()
_hasher = PasswordHasher()

# Pre-computed so unknown-email logins spend the same time hashing (no user enumeration by timing).
DUMMY_HASH = _hasher.hash("oncogon-dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def now() -> datetime:
    return datetime.now(timezone.utc)


def create_jwt(subject: uuid.UUID, purpose: str, ttl: timedelta, extra: dict | None = None) -> str:
    issued = now()
    payload = {
        "sub": str(subject),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued,
        "exp": issued + ttl,
        "jti": uuid.uuid4().hex,
        "typ": purpose,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str, purpose: str) -> dict:
    """Raises jwt.PyJWTError when the token is invalid, expired, or for another purpose."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "sub", "typ"]},
    )
    if payload.get("typ") != purpose:
        raise jwt.InvalidTokenError("Wrong token type")
    return payload


def new_refresh_token() -> tuple[str, str]:
    """Returns (token for the client, SHA-256 digest to store)."""
    token = secrets.token_urlsafe(48)
    return token, sha256(token)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_reset_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"
