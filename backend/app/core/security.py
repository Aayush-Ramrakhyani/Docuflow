"""
JWT token creation/verification and Argon2id password hashing.
Never store raw passwords or log tokens.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# Argon2id with OWASP-recommended parameters
_ph = PasswordHasher(
    time_cost=2,        # 2 iterations
    memory_cost=65536,  # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": secrets.token_hex(32),  # unique token ID for revocation
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises JWTError on any failure.
    Does NOT touch the database — caller must verify user still exists and is active.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise

    if payload.get("type") != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")

    return payload


def generate_api_key() -> tuple[str, str]:
    """
    Returns (raw_key, hashed_key).
    raw_key is shown to user once; hashed_key is stored.
    Format: df_<32 hex chars>
    """
    raw = "df_" + secrets.token_hex(32)
    hashed = hash_password(raw)
    return raw, hashed


def generate_webhook_secret() -> str:
    return secrets.token_hex(32)


def constant_time_compare(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode(), b.encode())
