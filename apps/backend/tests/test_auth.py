"""Auth endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    res = await client.post("/api/v1/auth/register", json={
        "email": "test@scalper.io",
        "password": "testpass123",
        "full_name": "Test Trader",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "test@scalper.io"

    # Login
    res = await client.post("/api/v1/auth/login", json={
        "email": "test@scalper.io",
        "password": "testpass123",
    })
    assert res.status_code == 200
    tokens = res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Authenticated route
    res = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {tokens['access_token']}"
    })
    assert res.status_code == 200
    assert res.json()["email"] == "test@scalper.io"


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "wrongpass",
    })
    assert res.status_code == 401
