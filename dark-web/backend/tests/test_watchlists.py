import pytest

from tests.conftest import bearer

BASE = "/api/v1/watchlists"
PAYLOAD = {"name": "Acme Corp", "keywords": ["acme"], "domains": ["acme.com"], "emails": []}


class TestListWatchlists:
    async def test_empty_for_new_user(self, client, analyst_user):
        resp = await client.get(BASE + "/", headers=bearer(analyst_user))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_auth(self, client):
        resp = await client.get(BASE + "/")
        assert resp.status_code == 401


class TestCreateWatchlist:
    async def test_analyst_creates(self, client, analyst_user):
        resp = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Acme Corp"
        assert body["keywords"] == ["acme"]
        assert body["domains"] == ["acme.com"]
        assert body["owner_id"] == analyst_user.id

    async def test_readonly_forbidden(self, client, readonly_user):
        resp = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(readonly_user))
        assert resp.status_code == 403

    async def test_keywords_deduped_and_lowercased(self, client, analyst_user):
        resp = await client.post(
            BASE + "/",
            json={"name": "Test", "keywords": ["Acme", "ACME", "acme", " acme "], "domains": [], "emails": []},
            headers=bearer(analyst_user),
        )
        assert resp.status_code == 201
        assert resp.json()["keywords"] == ["acme"]

    async def test_name_required(self, client, analyst_user):
        resp = await client.post(
            BASE + "/",
            json={"name": "", "keywords": [], "domains": [], "emails": []},
            headers=bearer(analyst_user),
        )
        assert resp.status_code == 422


class TestOwnership:
    async def test_owner_can_read(self, client, analyst_user):
        create = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        wid = create.json()["id"]
        resp = await client.get(f"{BASE}/{wid}", headers=bearer(analyst_user))
        assert resp.status_code == 200

    async def test_other_analyst_cannot_read(self, client, analyst_user, readonly_user):
        create = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        wid = create.json()["id"]
        resp = await client.get(f"{BASE}/{wid}", headers=bearer(readonly_user))
        assert resp.status_code == 403

    async def test_admin_sees_all(self, client, admin_user, analyst_user):
        await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        resp = await client.get(BASE + "/", headers=bearer(admin_user))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestUpdateWatchlist:
    async def test_owner_updates(self, client, analyst_user):
        create = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        wid = create.json()["id"]
        updated = {"name": "Acme Updated", "keywords": ["acme", "acmecorp"], "domains": [], "emails": []}
        resp = await client.put(f"{BASE}/{wid}", json=updated, headers=bearer(analyst_user))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Acme Updated"
        assert "acmecorp" in resp.json()["keywords"]


class TestDeleteWatchlist:
    async def test_soft_delete(self, client, analyst_user):
        create = await client.post(BASE + "/", json=PAYLOAD, headers=bearer(analyst_user))
        wid = create.json()["id"]
        resp = await client.delete(f"{BASE}/{wid}", headers=bearer(analyst_user))
        assert resp.status_code == 204

        list_resp = await client.get(BASE + "/", headers=bearer(analyst_user))
        assert all(w["id"] != wid for w in list_resp.json())
