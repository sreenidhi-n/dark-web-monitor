from unittest.mock import patch

import pytest

from tests.conftest import bearer


ONION = "http://abcdefghij1234567890abcdefghij12.onion"
ONION2 = "http://zyxwvutsrq0987654321zyxwvutsrq09.onion"


class TestListSources:
    async def test_empty(self, client, admin_user):
        resp = await client.get("/api/v1/sources/", headers=bearer(admin_user))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requires_auth(self, client):
        resp = await client.get("/api/v1/sources/")
        assert resp.status_code == 401


class TestCreateSource:
    async def test_admin_creates(self, client, admin_user):
        resp = await client.post(
            "/api/v1/sources/",
            json={"name": "Paste Site", "onion_url": ONION, "crawl_frequency_hours": 12},
            headers=bearer(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Paste Site"
        assert body["onion_url"] == ONION
        assert body["is_active"] is True

    async def test_analyst_creates(self, client, analyst_user):
        resp = await client.post(
            "/api/v1/sources/",
            json={"name": "Forum", "onion_url": ONION, "crawl_frequency_hours": 24},
            headers=bearer(analyst_user),
        )
        assert resp.status_code == 201

    async def test_readonly_forbidden(self, client, readonly_user):
        resp = await client.post(
            "/api/v1/sources/",
            json={"name": "Forum", "onion_url": ONION, "crawl_frequency_hours": 24},
            headers=bearer(readonly_user),
        )
        assert resp.status_code == 403

    async def test_invalid_url_not_onion(self, client, admin_user):
        resp = await client.post(
            "/api/v1/sources/",
            json={"name": "Bad", "onion_url": "http://google.com", "crawl_frequency_hours": 1},
            headers=bearer(admin_user),
        )
        assert resp.status_code == 422

    async def test_invalid_url_no_scheme(self, client, admin_user):
        resp = await client.post(
            "/api/v1/sources/",
            json={"name": "Bad", "onion_url": "ftp://abc.onion", "crawl_frequency_hours": 1},
            headers=bearer(admin_user),
        )
        assert resp.status_code == 422

    async def test_duplicate_409(self, client, admin_user):
        payload = {"name": "S1", "onion_url": ONION, "crawl_frequency_hours": 1}
        await client.post("/api/v1/sources/", json=payload, headers=bearer(admin_user))
        resp = await client.post("/api/v1/sources/", json=payload, headers=bearer(admin_user))
        assert resp.status_code == 409


class TestGetSource:
    async def test_get_by_id(self, client, admin_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "S", "onion_url": ONION, "crawl_frequency_hours": 6},
            headers=bearer(admin_user),
        )
        sid = create.json()["id"]
        resp = await client.get(f"/api/v1/sources/{sid}", headers=bearer(admin_user))
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    async def test_not_found(self, client, admin_user):
        resp = await client.get("/api/v1/sources/99999", headers=bearer(admin_user))
        assert resp.status_code == 404


class TestUpdateSource:
    async def test_update(self, client, admin_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "Old", "onion_url": ONION, "crawl_frequency_hours": 24},
            headers=bearer(admin_user),
        )
        sid = create.json()["id"]
        resp = await client.put(
            f"/api/v1/sources/{sid}",
            json={"name": "New", "onion_url": ONION2, "crawl_frequency_hours": 48},
            headers=bearer(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["crawl_frequency_hours"] == 48


class TestDeleteSource:
    async def test_admin_soft_deletes(self, client, admin_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "Del", "onion_url": ONION, "crawl_frequency_hours": 1},
            headers=bearer(admin_user),
        )
        sid = create.json()["id"]
        resp = await client.delete(f"/api/v1/sources/{sid}", headers=bearer(admin_user))
        assert resp.status_code == 204

        # active_only=True (default) should no longer return it
        list_resp = await client.get("/api/v1/sources/", headers=bearer(admin_user))
        ids = [s["id"] for s in list_resp.json()]
        assert sid not in ids

    async def test_analyst_forbidden(self, client, analyst_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "Del", "onion_url": ONION, "crawl_frequency_hours": 1},
            headers=bearer(analyst_user),
        )
        sid = create.json()["id"]
        resp = await client.delete(f"/api/v1/sources/{sid}", headers=bearer(analyst_user))
        assert resp.status_code == 403


class TestTriggerCrawl:
    async def test_enqueues_task(self, client, admin_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "Crawlable", "onion_url": ONION, "crawl_frequency_hours": 1},
            headers=bearer(admin_user),
        )
        sid = create.json()["id"]

        with patch("app.routers.sources.crawl_source") as mock_task:
            mock_task.delay.return_value = None
            resp = await client.post(
                f"/api/v1/sources/{sid}/crawl", headers=bearer(admin_user)
            )
        assert resp.status_code == 202
        mock_task.delay.assert_called_once_with(sid)

    async def test_inactive_source_rejected(self, client, admin_user):
        create = await client.post(
            "/api/v1/sources/",
            json={"name": "Gone", "onion_url": ONION, "crawl_frequency_hours": 1},
            headers=bearer(admin_user),
        )
        sid = create.json()["id"]
        await client.delete(f"/api/v1/sources/{sid}", headers=bearer(admin_user))

        with patch("app.routers.sources.crawl_source"):
            resp = await client.post(
                f"/api/v1/sources/{sid}/crawl", headers=bearer(admin_user)
            )
        assert resp.status_code == 400
