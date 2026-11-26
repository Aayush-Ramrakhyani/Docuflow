"""
Authentication business logic: register, login, token refresh, password reset.

No HTTP concerns live here — endpoints are thin wrappers over these methods, and
tests can call them directly. Two security properties are deliberately engineered:
  - Login is timing-safe (we hash even when the user doesn't exist).
  - Password reset never reveals whether an email is registered.
"""

import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.repositories.audit_repository import AuditRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, UserResponse

settings = get_settings()


def _generate_org_slug(name: str) -> str:
    # Slugify the name and append random hex so slugs are unique without a DB check
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:80] + "-" + secrets.token_hex(4)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.orgs = OrganizationRepository(db)
        self.audit = AuditRepository(db)

    async def register(
        self,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
        ip_address: str | None = None,
    ) -> tuple[AuthResponse, str]:
        # Reject duplicate signups up front
        existing = await self.users.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        verification_token = secrets.token_urlsafe(48)  # One-time email-verification token
        hashed = hash_password(password)                # Never store the raw password
        user = await self.users.create(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            verification_token=verification_token,
        )

        # New signup bootstraps its own org; the registrant becomes its owner
        slug = _generate_org_slug(organization_name)
        org = await self.orgs.create(name=organization_name, slug=slug)
        await self.orgs.create_membership(
            organization_id=org.id, user_id=user.id, role="owner"
        )

        await self.audit.log(
            action="user.register",
            actor_id=user.id,
            organization_id=org.id,
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )

        # Issue tokens immediately so the user is logged in right after registering
        access_token = create_access_token(str(user.id), {"org_id": str(org.id)})
        refresh_token = create_refresh_token(str(user.id))
        await self.users.update_last_login(user.id)

        return AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ), refresh_token

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> tuple[AuthResponse, str]:
        user = await self.users.get_by_email(email)

        # Timing-safe: hash a dummy value even when the user doesn't exist, so the
        # response time doesn't reveal whether the email is registered.
        if not user:
            hash_password("dummy_to_prevent_timing_attack")
            await self.audit.log(
                action="user.login.failed",
                metadata={"email": email, "reason": "user_not_found"},
                success=False,
                failure_reason="user_not_found",
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",  # Generic message — no account enumeration
            )

        if not verify_password(password, user.hashed_password):
            await self.audit.log(
                action="user.login.failed",
                actor_id=user.id,
                metadata={"reason": "wrong_password"},
                success=False,
                failure_reason="wrong_password",
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:  # Correct credentials but deactivated account
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated",
            )

        # Transparently upgrade the hash if Argon2 params have since been strengthened
        if password_needs_rehash(user.hashed_password):
            await self.users.set_password(user.id, hash_password(password))

        # Embed the user's default org in the access token claims
        memberships = await self.orgs.list_user_memberships(user.id)
        default_org_id = str(memberships[0].organization_id) if memberships else None

        access_token = create_access_token(
            str(user.id), {"org_id": default_org_id} if default_org_id else {}
        )
        refresh_token = create_refresh_token(str(user.id))
        await self.users.update_last_login(user.id)

        await self.audit.log(
            action="user.login",
            actor_id=user.id,
            organization_id=memberships[0].organization_id if memberships else None,
            ip_address=ip_address,
        )

        return AuthResponse(
            user=UserResponse.model_validate(user),
            access_token=access_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ), refresh_token

    async def request_password_reset(self, email: str) -> str | None:
        """Returns the reset token (for email delivery), or None if user not found."""
        user = await self.users.get_by_email(email)
        if not user:
            return None  # Silently no-op — caller still returns 200 to prevent enumeration

        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(hours=1)  # Short-lived reset window
        await self.users.set_reset_token(user.id, token, expires_at)
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        # Repository only returns a user if the token matches AND hasn't expired
        user = await self.users.get_by_reset_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        hashed = hash_password(new_password)
        await self.users.set_password(user.id, hashed)  # Also clears the used reset token
        await self.audit.log(
            action="user.password_reset",
            actor_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
        )

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        user = await self.users.get_by_id(user_id)
        # Require the current password — prevents hijacked-session password takeover
        if not user or not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        hashed = hash_password(new_password)
        await self.users.set_password(user.id, hashed)
