"""Organization management endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_member, require_owner
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    CreateOrganizationRequest,
    InviteMemberRequest,
    MembershipResponse,
    OrganizationResponse,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/my", response_model=list[OrganizationResponse])
async def list_my_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Return all organizations the current user belongs to."""
    repo = OrganizationRepository(db)
    memberships = await repo.list_user_memberships(current_user.id)
    return [OrganizationResponse.model_validate(m.organization) for m in memberships]


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = OrganizationRepository(db)
    org = await repo.get_by_id(organization_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    body: UpdateOrganizationRequest,
    auth: Annotated[tuple, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = OrganizationRepository(db)
    values = body.model_dump(exclude_none=True)
    if values:
        await repo.update(organization_id, **values)
    org = await repo.get_by_id(organization_id)
    return OrganizationResponse.model_validate(org)


@router.get("/{organization_id}/members", response_model=list[MembershipResponse])
async def list_members(
    organization_id: UUID,
    auth: Annotated[tuple, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = OrganizationRepository(db)
    memberships = await repo.list_memberships(organization_id)
    result = []
    for m in memberships:
        resp = MembershipResponse.model_validate(m)
        if m.user:
            resp.user_email = m.user.email
            resp.user_full_name = m.user.full_name
            resp.user_avatar_url = m.user.avatar_url
        result.append(resp)
    return result


@router.post("/{organization_id}/members/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    organization_id: UUID,
    body: InviteMemberRequest,
    auth: Annotated[tuple, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    org_repo = OrganizationRepository(db)

    invitee = await user_repo.get_by_email(body.email)
    if not invitee:
        raise HTTPException(status_code=404, detail="No user found with that email")

    existing = await org_repo.get_membership(organization_id, invitee.id)
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = await org_repo.create_membership(
        organization_id=organization_id,
        user_id=invitee.id,
        role=body.role,
        invited_by_id=current_user.id,
    )
    return {"message": "Member added successfully", "membership_id": str(membership.id)}


@router.patch("/{organization_id}/members/{membership_id}/role")
async def update_member_role(
    organization_id: UUID,
    membership_id: UUID,
    body: UpdateMemberRoleRequest,
    auth: Annotated[tuple, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    repo = OrganizationRepository(db)

    from sqlalchemy import select
    from app.models.organization import OrganizationMembership

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    # Prevent demoting the owner
    if membership.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot change the role of the organization owner")

    # Prevent self-role-change
    if membership.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Cannot change your own role")

    await repo.update_membership_role(membership_id, body.role)
    return {"message": "Role updated"}


@router.delete("/{organization_id}/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    organization_id: UUID,
    membership_id: UUID,
    auth: Annotated[tuple, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    current_user, _ = auth
    repo = OrganizationRepository(db)

    from sqlalchemy import select
    from app.models.organization import OrganizationMembership

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership.role == "owner":
        raise HTTPException(status_code=403, detail="Cannot remove the organization owner")

    if membership.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="Cannot remove yourself — transfer ownership first")

    await repo.delete_membership(membership_id)
