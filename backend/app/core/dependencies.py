"""
FastAPI dependency injection: auth, DB sessions, rate limiting helpers.
Every private endpoint must use require_current_user or require_org_member.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import decode_token

settings = get_settings()


async def get_token_from_header(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.removeprefix("Bearer ").strip()


async def get_current_user_id(
    token: Annotated[str, Depends(get_token_from_header)],
) -> str:
    """Extract and validate user_id from access token without DB lookup."""
    try:
        payload = decode_token(token, expected_type="access")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return user_id


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    """Fetch authenticated user from DB, verify active."""
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


async def get_current_active_user(
    current_user: Annotated["User", Depends(get_current_user)],  # type: ignore[name-defined]  # noqa: F821
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    return current_user


class RequireOrgRole:
    """
    Dependency factory that verifies the current user is a member of
    the requested organization with at least the given role level.
    """

    ROLE_RANK = {"member": 0, "admin": 1, "owner": 2}

    def __init__(self, minimum_role: str = "member"):
        self.minimum_role = minimum_role

    async def __call__(
        self,
        organization_id: UUID,
        current_user: Annotated["User", Depends(get_current_user)],  # type: ignore[name-defined]  # noqa: F821
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> tuple["User", "OrganizationMembership"]:  # type: ignore[name-defined]  # noqa: F821
        from app.repositories.organization_repository import OrganizationRepository

        repo = OrganizationRepository(db)
        membership = await repo.get_membership(
            organization_id=organization_id, user_id=current_user.id
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        required = self.ROLE_RANK.get(self.minimum_role, 0)
        actual = self.ROLE_RANK.get(membership.role, 0)
        if actual < required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.minimum_role}' required; you have '{membership.role}'",
            )
        return current_user, membership


require_member = RequireOrgRole("member")
require_admin = RequireOrgRole("admin")
require_owner = RequireOrgRole("owner")
