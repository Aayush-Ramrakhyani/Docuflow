"""
Auth business logic: register, login, token refresh, password reset.
No HTTP concerns — called by API routes and can be called from tests directly.
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
        existing = await self.users.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        verification_token = secrets.token_urlsafe(48)
        hashed = hash_password(password)
        user = await self.users.create(
            email=email,
            hashed_password=hashed,
            full_name=full_name,
            verification_token=verification_token,
        )

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

        # Constant-time failure path: always hash even if user not found
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
                detail="Invalid email or password",
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

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deactivated",
            )

        # Re-hash if Argon2 params have changed
        if password_needs_rehash(user.hashed_password):
            await self.users.set_password(user.id, hash_password(password))

        # Get default org for token claims
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
        """Returns the reset token (for email delivery). Returns None if user not found."""
        user = await self.users.get_by_email(email)
        if not user:
            return None  # Don't reveal whether email exists

        token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + timedelta(hours=1)
        await self.users.set_reset_token(user.id, token, expires_at)
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        user = await self.users.get_by_reset_token(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        hashed = hash_password(new_password)
        await self.users.set_password(user.id, hashed)
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
        if not user or not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )
        hashed = hash_password(new_password)
        await self.users.set_password(user.id, hashed)
