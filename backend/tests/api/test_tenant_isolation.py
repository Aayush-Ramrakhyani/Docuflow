"""
Tenant isolation tests — verify cross-tenant data access is blocked.
These tests are critical: a failure means a data breach.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Organization, OrganizationMembership, User
from app.core.security import hash_password


async def _create_user_and_org(
    db: AsyncSession, email: str, org_name: str
) -> tuple[User, Organization, str]:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("TestPass123"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    org = Organization(
        id=uuid.uuid4(),
        name=org_name,
        slug=f"org-{uuid.uuid4().hex[:8]}",
    )
    db.add(org)
    await db.flush()
    membership = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    await db.flush()
    return user, org, "TestPass123"


@pytest.mark.asyncio
async def test_cannot_access_another_orgs_documents(
    client: AsyncClient, db_session: AsyncSession
):
    """User A must not be able to list User B's documents."""
    user_a, org_a, pw = await _create_user_and_org(db_session, "usera@test.com", "Org A")
    user_b, org_b, _ = await _create_user_and_org(db_session, "userb@test.com", "Org B")

    # Login as User A
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "usera@test.com", "password": pw},
    )
    token_a = login.json()["access_token"]

    # Try to access Org B's documents as User A
    response = await client.get(
        f"/api/v1/organizations/{org_b.id}/documents",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 403, (
        f"User A must not access Org B's documents. Got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_cannot_access_another_orgs_members(
    client: AsyncClient, db_session: AsyncSession
):
    """User A must not be able to list User B's organization members."""
    user_a, org_a, pw = await _create_user_and_org(db_session, "membera@test.com", "Org A2")
    user_b, org_b, _ = await _create_user_and_org(db_session, "memberb@test.com", "Org B2")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "membera@test.com", "password": pw},
    )
    token_a = login.json()["access_token"]

    response = await client.get(
        f"/api/v1/organizations/{org_b.id}/members",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_access_another_orgs_analytics(
    client: AsyncClient, db_session: AsyncSession
):
    user_a, org_a, pw = await _create_user_and_org(db_session, "analyticsa@test.com", "Org A3")
    user_b, org_b, _ = await _create_user_and_org(db_session, "analyticsb@test.com", "Org B3")

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "analyticsa@test.com", "password": pw},
    )
    token_a = login.json()["access_token"]

    response = await client.get(
        f"/api/v1/organizations/{org_b.id}/analytics/overview",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_blocked(client: AsyncClient):
    """Every private endpoint must reject requests without a valid token."""
    org_id = uuid.uuid4()
    for path in [
        f"/api/v1/organizations/{org_id}/documents",
        f"/api/v1/organizations/{org_id}/members",
        f"/api/v1/organizations/{org_id}/analytics/overview",
        "/api/v1/auth/me",
    ]:
        resp = await client.get(path)
        assert resp.status_code == 401, f"Expected 401 for {path}, got {resp.status_code}"
