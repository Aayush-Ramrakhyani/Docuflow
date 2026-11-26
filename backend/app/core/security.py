"""
Security primitives: JWT token creation/verification and Argon2id password hashing.

This module is the single source of truth for all cryptographic operations.
Rules enforced here:
  - Passwords are only ever stored as Argon2id hashes (never plaintext).
  - Access tokens are short-lived; refresh tokens carry a unique jti for revocation.
  - Tokens are never logged and raw passwords never leave this module.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# Argon2id hasher configured with OWASP-recommended parameters.
_ph = PasswordHasher(
    time_cost=2,        # Number of iterations — higher = slower = harder to brute force
    memory_cost=65536,  # 64 MB of memory per hash — resists GPU/ASIC cracking
    parallelism=2,      # Parallel threads used during hashing
    hash_len=32,        # Length of the resulting hash in bytes
    salt_len=16,        # Length of the random salt in bytes
)


def hash_password(plain: str) -> str:
    # Produces a self-describing Argon2id hash (embeds salt + params)
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        # Constant-time verification handled internally by argon2-cffi
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Any failure (wrong password, corrupt hash) is treated as "no match"
        return False


def password_needs_rehash(hashed: str) -> bool:
    # True when stored hash used weaker params than the current config → re-hash on next login
    return _ph.check_needs_rehash(hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "sub": subject,                                   # Subject = user id
        "type": "access",                                 # Guards against using a refresh token as access
        "iat": datetime.now(UTC),                         # Issued-at timestamp
        "exp": datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),  # Short expiry
    }
    if extra:
        payload.update(extra)  # Optional claims (e.g. org_id) merged in
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    payload: dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": secrets.token_hex(32),  # Unique token ID — enables per-token revocation later
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),  # Long expiry
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises JWTError on any failure.
    Does NOT touch the database — caller must verify the user still exists and is active.
    """
    try:
        # Signature + expiry are validated here; tampered/expired tokens raise JWTError
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise

    # Reject a token whose type doesn't match the context it's being used in
    if payload.get("type") != expected_type:
        raise JWTError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")

    return payload


def generate_api_key() -> tuple[str, str]:
    """
    Returns (raw_key, hashed_key).
    raw_key is shown to the user exactly once; only hashed_key is persisted.
    Format: df_<32 hex chars>
    """
    raw = "df_" + secrets.token_hex(32)  # Prefixed so leaked keys are grep-able in logs/scanners
    hashed = hash_password(raw)           # Stored as an Argon2id hash, like a password
    return raw, hashed


def generate_webhook_secret() -> str:
    # Shared secret used to HMAC-sign outgoing webhook payloads
    return secrets.token_hex(32)


def constant_time_compare(a: str, b: str) -> bool:
    # Timing-safe comparison — prevents leaking secrets via response-time analysis
    return secrets.compare_digest(a.encode(), b.encode())
