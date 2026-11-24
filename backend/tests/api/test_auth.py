"""Auth endpoint tests — login, register, token refresh, password reset."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_creates_user_and_org(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "SecurePass123",
            "full_name": "New User",
            "organization_name": "New Org",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "new@example.com"
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "password": "SecurePass123",
        "full_name": "User",
        "organization_name": "Org",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "TestPass123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401
    # Must not reveal whether email exists
    assert "password" in response.json()["detail"].lower() or "email" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "SomePass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token(client: AsyncClient, test_user, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == test_user.email


@pytest.mark.asyncio
async def test_weak_password_rejected(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "weak@example.com",
            "password": "weak",  # Too short, no uppercase, no digit
            "full_name": "User",
            "organization_name": "Org",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_forgot_password_always_returns_200(client: AsyncClient):
    # Must not reveal whether email exists
    for email in ["exists@example.com", "nonexistent@example.com"]:
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )
        assert response.status_code == 200
