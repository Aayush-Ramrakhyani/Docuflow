"""
FastAPI dependency-injection helpers for authentication and authorization.

Layered access control:
  1. get_token_from_header  — pulls the Bearer token off the request
  2. get_current_user_id    — validates the JWT (no DB hit)
  3. get_current_user       — loads the user and checks it's active
  4. RequireOrgRole         — verifies org membership AND minimum role

Every private endpoint must depend on get_current_user or a RequireOrgRole instance.
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
    # Reject anything that isn't a well-formed "Bearer <token>" header
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
    """Extract and validate user_id from the access token without a DB lookup."""
    try:
        # Signature/expiry/type all checked here
        payload = decode_token(token, expected_type="access")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id: str | None = payload.get("sub")
    if not user_id:  # Token decoded but carries no subject → treat as invalid
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return user_id


async def get_current_user(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    """Fetch the authenticated user from the DB and verify the account is active."""
    # Imported lazily to avoid a circular import at module load time
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(UUID(user_id))
    if not user:  # Token was valid but the user was deleted since it was issued
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:  # Deactivated accounts are blocked even with a valid token
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


async def get_current_active_user(
    current_user: Annotated["User", Depends(get_current_user)],  # type: ignore[name-defined]  # noqa: F821
) -> "User":  # type: ignore[name-defined]  # noqa: F821
    # Alias dependency for readability at call sites
    return current_user


class RequireOrgRole:
    """
    Dependency factory: verifies the current user belongs to the requested
    organization with AT LEAST the given role. This is the primary defense
    against IDOR / cross-tenant access at the application layer.
    """

    # Ordinal ranking so "admin" satisfies a "member" requirement, etc.
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
        # Membership lookup doubles as the tenant-ownership check for this org
        membership = await repo.get_membership(
            organization_id=organization_id, user_id=current_user.id
        )
        if not membership:  # Not a member → 403, never reveal whether the org exists
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        required = self.ROLE_RANK.get(self.minimum_role, 0)
        actual = self.ROLE_RANK.get(membership.role, 0)
        if actual < required:  # Member exists but lacks the required privilege level
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{self.minimum_role}' required; you have '{membership.role}'",
            )
        return current_user, membership


# Pre-built dependency instances for the three privilege tiers.
require_member = RequireOrgRole("member")
require_admin = RequireOrgRole("admin")
require_owner = RequireOrgRole("owner")
