"""
Organization and membership data access.

Handles the tenant records themselves plus the user↔org join table. Membership
lookups here back the RequireOrgRole dependency, so correctness of get_membership
is security-critical.
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.organization import Organization, OrganizationMembership


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug.lower())
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, slug: str) -> Organization:
        org = Organization(name=name, slug=slug.lower())
        self.db.add(org)
        await self.db.flush()  # Populate org.id for the caller
        return org

    async def update(self, org_id: uuid.UUID, **values) -> None:
        if values:  # No-op if there's nothing to change
            await self.db.execute(
                update(Organization).where(Organization.id == org_id).values(**values)
            )

    async def get_membership(
        self, organization_id: uuid.UUID, user_id: uuid.UUID
    ) -> OrganizationMembership | None:
        # Security-critical: this (user, org) lookup is the tenant-access check
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_memberships(self, organization_id: uuid.UUID) -> list[OrganizationMembership]:
        # selectinload eager-loads each member's user in one extra query (avoids N+1)
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .options(selectinload(OrganizationMembership.user))
        )
        return list(result.scalars().all())

    async def list_user_memberships(self, user_id: uuid.UUID) -> list[OrganizationMembership]:
        # Eager-load the organization so callers can read org details without N+1
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
            .options(selectinload(OrganizationMembership.organization))
        )
        return list(result.scalars().all())

    async def create_membership(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        invited_by_id: uuid.UUID | None = None,
    ) -> OrganizationMembership:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            invited_by_id=invited_by_id,  # Null for the founding owner
        )
        self.db.add(membership)
        await self.db.flush()
        return membership

    async def update_membership_role(
        self, membership_id: uuid.UUID, role: str
    ) -> None:
        await self.db.execute(
            update(OrganizationMembership)
            .where(OrganizationMembership.id == membership_id)
            .values(role=role)
        )

    async def delete_membership(self, membership_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(OrganizationMembership).where(OrganizationMembership.id == membership_id)
        )
        membership = result.scalar_one_or_none()
        if membership:  # Idempotent — deleting an already-gone membership is a no-op
            await self.db.delete(membership)

    async def count_members(self, organization_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count()).where(
                OrganizationMembership.organization_id == organization_id
            )
        )
        return result.scalar_one()
