"""
Organization & membership schemas.

Slug and role values are validated here so malformed tenants or privilege strings
never reach the service layer. Note: "owner" is intentionally NOT an assignable
role via the API — it's granted only to the founder at registration.
"""

import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255, strip_whitespace=True)
    slug: str | None = Field(default=None, min_length=2, max_length=100)  # Auto-generated if omitted

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower().strip()
        # URL-safe: lowercase alphanumeric + internal hyphens only
        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens, no leading/trailing hyphens")
        return v


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255, strip_whitespace=True)
    logo_url: str | None = None


class OrganizationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    slug: str
    logo_url: str | None
    plan: str
    documents_used: int
    documents_limit: int
    is_active: bool


class InviteMemberRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # Basic email shape check
    role: str = Field(default="member")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        # Only non-owner roles are assignable — prevents granting ownership via invite
        if v not in ("member", "admin"):
            raise ValueError("Role must be 'member' or 'admin'")
        return v


class UpdateMemberRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        # Same restriction as invites — no promoting anyone to "owner" through the API
        if v not in ("member", "admin"):
            raise ValueError("Role must be 'member' or 'admin'")
        return v


class MembershipResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    user_id: UUID
    organization_id: UUID
    role: str
    # Flattened from the joined user record by the endpoint (optional to keep model reusable)
    user_email: str | None = None
    user_full_name: str | None = None
    user_avatar_url: str | None = None
