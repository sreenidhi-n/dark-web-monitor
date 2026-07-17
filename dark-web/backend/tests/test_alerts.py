from datetime import datetime, timezone

import pytest

from app.models.alert import Alert, AlertChannel
from tests.conftest import bearer

WL_PAYLOAD = {"name": "Test WL", "keywords": ["leak"], "domains": [], "emails": []}
CFG_BASE = "/api/v1/alerts/config"
HIST_BASE = "/api/v1/alerts/history"


async def _create_watchlist(client, user):
    resp = await client.post("/api/v1/watchlists/", json=WL_PAYLOAD, headers=bearer(user))
    assert resp.status_code == 201
    return resp.json()["id"]


class TestAlertConfig:
    async def test_empty_list(self, client, analyst_user):
        resp = await client.get(CFG_BASE, headers=bearer(analyst_user))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_config(self, client, analyst_user):
        wid = await _create_watchlist(client, analyst_user)
        resp = await client.post(
            CFG_BASE,
            json={"watchlist_id": wid, "channel": "email", "destination": "alerts@acme.com"},
            headers=bearer(analyst_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["channel"] == "email"
        assert body["destination"] == "alerts@acme.com"
        assert body["watchlist_id"] == wid

    async def test_create_config_wrong_watchlist_forbidden(self, client, analyst_user, admin_user):
        # admin creates a watchlist
        wid = await _create_watchlist(client, admin_user)
        # analyst tries to add a config for it
        resp = await client.post(
            CFG_BASE,
            json={"watchlist_id": wid, "channel": "slack", "destination": "https://hooks.slack.com/x"},
            headers=bearer(analyst_user),
        )
        assert resp.status_code == 403

    async def test_readonly_cannot_create_config(self, client, analyst_user, readonly_user):
        wid = await _create_watchlist(client, analyst_user)
        resp = await client.post(
            CFG_BASE,
            json={"watchlist_id": wid, "channel": "webhook", "destination": "https://siem.corp/hook"},
            headers=bearer(readonly_user),
        )
        assert resp.status_code == 403

    async def test_delete_config(self, client, analyst_user):
        wid = await _create_watchlist(client, analyst_user)
        create = await client.post(
            CFG_BASE,
            json={"watchlist_id": wid, "channel": "email", "destination": "x@y.com"},
            headers=bearer(analyst_user),
        )
        cid = create.json()["id"]
        resp = await client.delete(f"{CFG_BASE}/{cid}", headers=bearer(analyst_user))
        assert resp.status_code == 204

        list_resp = await client.get(CFG_BASE, headers=bearer(analyst_user))
        assert all(c["id"] != cid for c in list_resp.json())


class TestAlertHistory:
    async def test_empty_history(self, client, analyst_user):
        resp = await client.get(HIST_BASE, headers=bearer(analyst_user))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_acknowledge_alert(self, client, analyst_user, db):
        from app.models.finding import Finding
        from app.models.source import Source

        # Set up source + finding + watchlist + alert in the DB directly
        source = Source(name="S", onion_url="http://abc.onion", crawl_frequency_hours=1)
        db.add(source)
        await db.commit()
        await db.refresh(source)

        finding = Finding(
            source_id=source.id,
            url="http://abc.onion/page",
            content_hash="deadbeef" * 8,
            matched_keywords=["leak"],
        )
        db.add(finding)
        await db.commit()
        await db.refresh(finding)

        from app.models.watchlist import Watchlist
        wl = Watchlist(name="WL", owner_id=analyst_user.id, keywords=["leak"], domains=[], emails=[])
        db.add(wl)
        await db.commit()
        await db.refresh(wl)

        alert = Alert(
            watchlist_id=wl.id,
            finding_id=finding.id,
            channel=AlertChannel.email,
            delivered=True,
            acknowledged=False,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        # Acknowledge it
        resp = await client.post(
            f"{HIST_BASE}/{alert.id}/acknowledge", headers=bearer(analyst_user)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["acknowledged"] is True
        assert body["acknowledged_at"] is not None
