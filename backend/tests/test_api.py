import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import get_password_hash, verify_password, create_access_token, decode_access_token


@pytest.mark.asyncio
async def test_healthcheck():
    """Verify system health endpoint returns 200 OK and expected structure."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data


def test_security_password_hashing():
    """Verify bcrypt password hashing and verification."""
    password = "SuperSecurePassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_generation_and_decoding():
    """Verify JWT access token creation and payload extraction."""
    user_id = "11111111-2222-3333-4444-555555555555"
    token = create_access_token(subject=user_id)
    assert isinstance(token, str)
    
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == user_id


@pytest.mark.asyncio
async def test_unauthorized_admin_access():
    """Verify that unauthenticated requests to admin dashboard are rejected with 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/admin/dashboard")
    assert response.status_code == 401
