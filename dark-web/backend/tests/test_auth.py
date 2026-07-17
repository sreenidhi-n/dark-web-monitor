import pytest

from tests.conftest import bearer


class TestLogin:
    async def test_success(self, client, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "password"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert "access_token" in body

    async def test_wrong_password(self, client, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin@test.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_unknown_user(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@test.com", "password": "password"},
        )
        assert resp.status_code == 401


class TestLogout:
    async def test_logout(self, client, admin_user):
        resp = await client.post("/api/v1/auth/logout", headers=bearer(admin_user))
        assert resp.status_code == 200


class TestMe:
    async def test_me_with_jwt(self, client, admin_user):
        resp = await client.get("/api/v1/auth/me", headers=bearer(admin_user))
        assert resp.status_code == 200
        assert resp.json()["email"] == "admin@test.com"
        assert resp.json()["role"] == "admin"

    async def test_me_unauthenticated(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_api_key(self, client, analyst_user, db):
        # Generate an API key first
        resp = await client.post("/api/v1/auth/api-key", headers=bearer(analyst_user))
        assert resp.status_code == 200
        api_key = resp.json()["api_key"]

        # Use it
        resp = await client.get("/api/v1/auth/me", headers={"X-API-Key": api_key})
        assert resp.status_code == 200
        assert resp.json()["email"] == "analyst@test.com"


class TestApiKey:
    async def test_rotate_api_key(self, client, admin_user):
        resp = await client.post("/api/v1/auth/api-key", headers=bearer(admin_user))
        assert resp.status_code == 200
        key1 = resp.json()["api_key"]

        # Rotate again — should get a different key
        resp2 = await client.post("/api/v1/auth/api-key", headers=bearer(admin_user))
        assert resp2.status_code == 200
        key2 = resp2.json()["api_key"]
        assert key1 != key2
