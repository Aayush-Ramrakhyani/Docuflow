"""
User account model.

A user is a person who can log in. Passwords are stored ONLY as Argon2id hashes.
Users belong to organizations through OrganizationMembership (a user can be in
several orgs). Tenant data is never attached directly to a user — always via org.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel


class User(TimestampedModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)  # Login identifier
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)  # Argon2id hash — never plaintext
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)       # Deactivated users can't log in
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)    # Email ownership confirmed
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Platform-wide admin (RLS bypass)

    # Email verification / password reset — single-use, time-limited tokens
    verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reset_token: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True  # Reset tokens expire (checked on use)
    )

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # A user's memberships across all organizations they belong to
    memberships: Mapped[list["OrganizationMembership"]] = relationship(  # noqa: F821
        "OrganizationMembership", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
