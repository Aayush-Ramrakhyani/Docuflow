"""
Auth request/response schemas (Pydantic).

These define the validated shape of every auth payload crossing the API boundary.
Password-complexity rules live here so invalid input is rejected before it ever
reaches a service. Response models never expose sensitive fields (no password hash).
"""

import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# Re-export so endpoints can `from app.schemas.auth import MessageResponse`.
# The canonical definition lives in schemas.common.
from app.schemas.common import MessageResponse  # noqa: F401


# Shared password policy, applied by every schema that sets a password.
def _validate_password_complexity(v: str) -> str:
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr  # EmailStr rejects malformed addresses automatically
    password: str = Field(min_length=8, max_length=128)  # Length bounds before complexity check
    full_name: str = Field(min_length=1, max_length=255, strip_whitespace=True)
    organization_name: str = Field(min_length=1, max_length=255, strip_whitespace=True)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)  # No complexity check — just verifying


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)       # Opaque reset token from the email
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)  # Verified against stored hash
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Lifetime of the access token, in seconds


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}  # Allow building from a SQLAlchemy User object

    # Deliberately omits hashed_password, tokens, is_superadmin — never leak these
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool
    is_verified: bool


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str          # Refresh token is sent separately as an httpOnly cookie
    token_type: str = "bearer"
    expires_in: int
