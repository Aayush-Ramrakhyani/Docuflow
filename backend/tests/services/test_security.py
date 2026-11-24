"""Security utility tests — password hashing, token creation/verification."""

import pytest
import time
from jose import JWTError

from app.core.security import (
    hash_password,
    verify_password,
    password_needs_rehash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    constant_time_compare,
)


def test_password_hashes_are_unique():
    h1 = hash_password("SamePassword1")
    h2 = hash_password("SamePassword1")
    assert h1 != h2  # Different salts


def test_password_verification_correct():
    hashed = hash_password("MyPassword123")
    assert verify_password("MyPassword123", hashed) is True


def test_password_verification_wrong():
    hashed = hash_password("CorrectPass1")
    assert verify_password("WrongPass1", hashed) is False


def test_password_verification_timing_safe():
    """Ensure verify_password doesn't raise on bad hash — returns False."""
    assert verify_password("anything", "not-a-valid-hash") is False


def test_access_token_roundtrip():
    token = create_access_token("user-123", {"org_id": "org-456"})
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["org_id"] == "org-456"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token = create_refresh_token("user-123")
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert "jti" in payload  # Unique token ID present


def test_access_token_rejected_as_refresh():
    access_token = create_access_token("user-123")
    with pytest.raises(JWTError):
        decode_token(access_token, expected_type="refresh")


def test_refresh_token_rejected_as_access():
    refresh_token = create_refresh_token("user-123")
    with pytest.raises(JWTError):
        decode_token(refresh_token, expected_type="access")


def test_tampered_token_rejected():
    token = create_access_token("user-123")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(JWTError):
        decode_token(tampered)


def test_api_key_generation():
    raw, hashed = generate_api_key()
    assert raw.startswith("df_")
    assert len(raw) > 32
    # Raw key verifies against hash
    assert verify_password(raw, hashed)


def test_constant_time_compare():
    assert constant_time_compare("abc", "abc") is True
    assert constant_time_compare("abc", "xyz") is False
    assert constant_time_compare("", "") is True
