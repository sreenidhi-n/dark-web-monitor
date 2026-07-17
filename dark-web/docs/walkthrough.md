# Walkthrough — Dark Web Monitor

A practical guide to installing, configuring, and running Dark Web Monitor from scratch. By the end you'll have the full stack running, a source being crawled through Tor, and alerts firing when keywords match.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker 24+ and Docker Compose v2+ | `docker compose version` to verify |
| 4 GB+ free RAM | Elasticsearch claims ~1 GB on its own |
| Outbound internet on the host | Tor needs to bootstrap |
| `jq` (optional) | For pretty-printing API responses in the terminal |

---

## 1. Clone and configure

```bash
git clone https://github.com/sreenidhi-n/dark-web-monitor.git
cd dark-web-monitor
cp .env.example .env
```

Open `.env` and change the three required values:

| Variable | What to set |
|---|---|
| `POSTGRES_PASSWORD` | Any strong password |
| `REDIS_PASSWORD` | Any strong password |
| `SECRET_KEY` | `openssl rand -hex 32` — paste the output |

Everything else defaults to safe local values. Come back to `SMTP_*` and `SLACK_WEBHOOK_URL` later when you want real alert delivery.

---

## 2. Start the stack

```bash
make up
```

This brings up all eight services in the background (postgres, redis, elasticsearch, tor, backend, worker, beat, frontend, nginx). First startup takes **60–90 seconds** — Elasticsearch is slow to become healthy.

Watch progress:

```bash
make logs
```

You're ready when the backend prints:

```
INFO  [app.main] Starting Dark Web Monitor API
INFO  [app.search.client] Created Elasticsearch index: dwm_findings
```

---

## 3. Run database migrations

```bash
make migrate
```

Expected output:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add alert configs
```

---

## 4. Create the admin user

No default credentials exist. Bootstrap the first admin:

```bash
make create-admin email=admin@example.com password=yourpassword
```

The script is idempotent — running it twice with the same email is a no-op.

---

## 5. Log in to the UI

Open **http://localhost** in your browser. You'll land on the login screen.

Enter the email and password you just created. After login you'll see the dashboard:

- **Findings** — total indexed documents
- **Sources** — monitored `.onion` URLs
- **Watchlists** — active monitoring profiles
- **Alerts today** — keyword-match alerts triggered in the last 24 h

All four cards show `—` until data exists — that's expected.

---

## 6. Verify Tor connectivity

Before crawling anything, confirm the backend is routing through Tor:

```bash
make tor-check
```

Expected:
```
Tor OK: True
```

If you see `False`, the Tor container is still bootstrapping. Wait 30 seconds and retry. Check logs with:

```bash
docker compose logs tor
```

---

## 7. Add your first source

A **source** is a `.onion` URL the crawler will periodically visit and index.

**Via the UI:** navigate to **Sources** in the top nav → click **Add Source** → fill in the name, `.onion` URL, and how often to crawl (hours). Hit **Add Source**.

**Via the API:**

```bash
# Get an auth token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -d "username=admin@example.com&password=yourpassword" \
  | jq -r .access_token)

# Add a source
curl -s -X POST http://localhost/api/v1/sources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Paste Site",
    "onion_url": "http://examplexxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.onion",
    "crawl_frequency_hours": 6
  }' | jq
```

`crawl_frequency_hours` is how often Celery beat schedules an automatic crawl. Minimum effective value is `1`.

---

## 8. Create a watchlist

A **watchlist** defines what to look for: keywords (brand names, project names, internal terms), domains you own, and employee email addresses. Any finding whose content contains one or more of these triggers an alert.

**Via the UI:** navigate to **Watchlists** → click **New Watchlist**. Type a keyword and press `Enter` or comma to add it as a tag. Add as many as you need across the Keywords, Domains, and Emails fields. Hit **Create**.

**Via the API:**

```bash
curl -s -X POST http://localhost/api/v1/watchlists \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "keywords": ["acme", "acmecorp", "project-aurora"],
    "domains": ["acmecorp.com", "acme.io"],
    "emails": ["ceo@acmecorp.com", "hr@acmecorp.com"]
  }' | jq
```

Keywords are normalised to lowercase and deduplicated automatically.

---

## 9. Trigger a manual crawl

Don't wait for the scheduler — crawl a source immediately.

**Via the UI:** go to **Sources**, find the source row, click the **▷ play** button on the right.

**Via the API:**

```bash
# Replace 1 with your source's actual ID
curl -s -X POST http://localhost/api/v1/sources/1/crawl \
  -H "Authorization: Bearer $TOKEN" | jq
```

Response:
```json
{"detail": "Crawl enqueued for source 1"}
```

Watch the Celery worker pick it up:

```bash
make worker-logs
```

You'll see it:
1. Connect to the `.onion` site over Tor
2. Extract and index the content
3. Match against all active watchlists
4. Create `Alert` records for any hits

---

## 10. Browse and search findings

Navigate to **Findings** in the UI.

- **Browse mode** — paginated table of all indexed content, filterable by source and date
- **Search mode** — type 2+ characters in the search box to switch to full-text Elasticsearch search with highlighted snippets; clear the box to return to browse mode

Via the API — browse:

```bash
curl -s "http://localhost/api/v1/findings?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN" | jq
```

Via the API — full-text search:

```bash
curl -s "http://localhost/api/v1/findings/search?q=acmecorp" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 11. Configure alert delivery

Set up where alerts go when a keyword match fires. You can have multiple configs per watchlist (e.g. email + Slack).

**Via the UI:** go to **Alerts** → click **Notification Config** tab → **Add Config**. Select a watchlist, pick the channel (Email / Slack / Webhook), paste the destination, and save.

**Via the API:**

```bash
# Email
curl -s -X POST http://localhost/api/v1/alerts/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "watchlist_id": 1,
    "channel": "email",
    "destination": "security-team@acmecorp.com"
  }' | jq

# Slack
curl -s -X POST http://localhost/api/v1/alerts/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "watchlist_id": 1,
    "channel": "slack",
    "destination": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }' | jq

# Generic webhook (SIEM, Splunk HEC, etc.)
curl -s -X POST http://localhost/api/v1/alerts/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "watchlist_id": 1,
    "channel": "webhook",
    "destination": "https://your-siem.example.com/ingest"
  }' | jq
```

For SMTP delivery, set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM` in `.env` and restart the stack (`make restart`).

---

## 12. Review and acknowledge alerts

**Via the UI:** go to **Alerts** → **Alert History** tab. Each row shows the watchlist, channel, delivery status, and a checkmark button to acknowledge.

**Via the API:**

```bash
# List unacknowledged alerts
curl -s "http://localhost/api/v1/alerts/history?acknowledged=false" \
  -H "Authorization: Bearer $TOKEN" | jq

# Acknowledge alert ID 7
curl -s -X POST http://localhost/api/v1/alerts/history/7/acknowledge \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 13. Generate an API key

For SIEM integration or scripted workflows, create a permanent API key:

```bash
curl -s -X POST http://localhost/api/v1/auth/api-key \
  -H "Authorization: Bearer $TOKEN" | jq
```

Use it with `X-API-Key` instead of `Authorization: Bearer`:

```bash
curl -s http://localhost/api/v1/findings \
  -H "X-API-Key: <your_key>" | jq
```

Calling `POST /auth/api-key` again immediately rotates the key.

---

## 14. Export findings

Download all findings as a JSON file:

```bash
curl -s -X POST http://localhost/api/v1/export/findings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  -o findings_export.json
```

Scope by source or date:

```bash
-d '{"source_id": 1}'
-d '{"since": "2025-01-01"}'
```

---

## 15. Add more users

Use `make create-admin` to add additional admins. For analysts (can create sources/watchlists, cannot delete) or read-only users, insert directly:

```bash
# Generate a bcrypt hash first
HASH=$(docker compose exec backend python -c \
  "from passlib.context import CryptContext; \
   print(CryptContext(schemes=['bcrypt']).hash('theirpassword'))")

# Insert as analyst
make shell-db
```

Inside psql:

```sql
INSERT INTO users (email, password_hash, role, is_active)
VALUES ('analyst@acmecorp.com', '<hash>', 'analyst', true);

INSERT INTO users (email, password_hash, role, is_active)
VALUES ('viewer@acmecorp.com', '<hash>', 'readonly', true);
```

---

## 16. Run the test suite

```bash
cd backend
pip install -r requirements.txt   # aiosqlite + pytest-asyncio needed
pytest -v
```

Tests use an in-memory SQLite database — no running PostgreSQL, Redis, or Elasticsearch required. 38 tests across auth, sources, watchlists, alerts, and the scraper module.

---

## 17. Day-to-day operations

| Task | Command |
|---|---|
| Restart everything | `make restart` |
| Tail all logs | `make logs` |
| Tail only worker | `make worker-logs` |
| Open backend shell | `make shell-backend` |
| Open psql shell | `make shell-db` |
| Add migration | `make makemigration name=describe_change` |
| Apply migrations | `make migrate` |
| Run linter | `make lint` |

---

## 18. Stopping and cleanup

Stop containers (data volumes preserved):

```bash
make down
```

Full reset — destroys all volumes and data:

```bash
docker compose down -v
```

---

## API reference

Interactive Swagger UI — try every endpoint in the browser:

```
http://localhost/docs
```

ReDoc (read-only, better for sharing with a team):

```
http://localhost/redoc
```

---

## Troubleshooting

**Elasticsearch not healthy after 90 seconds**

Check for OOM:
```bash
docker compose logs elasticsearch | grep -i "error\|fatal"
```
Increase `ES_JAVA_OPTS` heap in `docker-compose.yml` if the host has available RAM. The default `-Xms512m -Xmx512m` is the minimum.

**`make migrate` fails — "could not connect to server"**

Postgres isn't ready yet. Run `make logs`, wait for `database system is ready to accept connections`, then retry.

**Tor check returns False**

Bootstrap takes up to 60 seconds on first start. Check:
```bash
docker compose logs tor | tail -30
```
Look for `Bootstrapped 100%`. If the host network blocks Tor, configure bridges in `infra/tor/torrc.example`.

**Login fails immediately after `make create-admin`**

Run `make migrate` first. The user table must exist before the admin script can write to it.

**JWT expired (401 after a few hours)**

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 480 min / 8 hours). Log in again. Increase the value in `.env` if needed.

**Worker task stuck / not picking up crawl jobs**

Check Redis is healthy:
```bash
docker compose ps redis
docker compose exec backend celery -A app.crawler.scheduler.celery_app inspect active
```
