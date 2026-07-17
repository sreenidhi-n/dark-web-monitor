# Walkthrough — Dark Web Monitor

A practical guide to installing, configuring, and operating Dark Web Monitor from scratch.

---

## Prerequisites

Before you start, make sure you have:

- **Docker** 24+ and **Docker Compose** v2+ installed
- At minimum **4 GB of free RAM** (Elasticsearch claims ~1 GB on its own)
- An outbound internet connection on the host (Tor needs to bootstrap)
- A working SMTP server, Slack webhook, or generic webhook URL if you want alerts delivered somewhere (optional — you can run without notifications)

---

## 1. Installation

```bash
git clone https://github.com/your-handle/dark-web-monitor.git
cd dark-web-monitor
```

---

## 2. Configuration

Copy the example environment file and open it in an editor:

```bash
cp .env.example .env
```

The minimum set of values you must change before starting:

| Variable | What to set |
|---|---|
| `POSTGRES_PASSWORD` | Any strong password |
| `REDIS_PASSWORD` | Any strong password |
| `SECRET_KEY` | Run `openssl rand -hex 32` and paste the output |

Everything else has safe defaults for local use. For production deployments, also review `SMTP_*` and `SLACK_WEBHOOK_URL` if you want alert delivery.

---

## 3. First Start

```bash
make up
```

This starts all eight services in the background. First startup takes about 60 seconds — Elasticsearch needs time to become healthy before the backend and workers connect.

Watch the logs until everything is green:

```bash
make logs
```

You're looking for the backend to print:

```
INFO  [app.main] Starting Dark Web Monitor API
INFO  [app.search.client] Created Elasticsearch index: dwm_findings
```

---

## 4. Database Setup

Run the Alembic migration to create all tables:

```bash
make migrate
```

Expected output:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial schema
```

---

## 5. Create Your Admin User

There are no default credentials. Create the first admin with:

```bash
make create-admin email=admin@example.com password=yourpassword
```

This script is idempotent — running it again with the same email is a no-op.

---

## 6. Open the Dashboard

Navigate to `http://localhost` in your browser. You will see the dashboard with four stat cards (all showing `—` until data exists) and an empty findings chart.

---

## 7. Verify Tor Connectivity

Before adding any sources, confirm that the backend is routing through Tor:

```bash
make tor-check
```

Expected output:
```
Tor OK: True
```

If you see `ERROR: not routing through Tor`, check the Tor container logs:

```bash
docker compose logs tor
```

Tor takes up to 30 seconds to bootstrap on first start. Wait and retry.

---

## 8. Add Your First Source

A **source** is a `.onion` URL that the crawler will periodically visit and index.

Use the API directly (the UI for this is coming in v0.4):

```bash
# First, get a token
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/login \
  -d "username=admin@example.com&password=yourpassword" \
  | jq -r .access_token)

# Add a source
curl -s -X POST http://localhost/api/v1/sources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Paste Site",
    "onion_url": "http://examplexxxxxxx.onion",
    "crawl_frequency_hours": 6
  }' | jq
```

`crawl_frequency_hours` controls how often Celery beat will schedule a crawl for this source. The minimum effective value is `1`.

---

## 9. Create a Watchlist

A **watchlist** defines what to look for: keywords (e.g. brand terms, internal project names), domain names, and email addresses belonging to your organization.

```bash
curl -s -X POST http://localhost/api/v1/watchlists \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "keywords": ["acme", "acmecorp", "acme internal"],
    "domains": ["acmecorp.com", "acme.io"],
    "emails": ["ceo@acmecorp.com", "hr@acmecorp.com"]
  }' | jq
```

Any finding whose scraped text contains one or more of these terms will trigger an alert.

---

## 10. Trigger a Manual Crawl

To crawl a source immediately rather than waiting for the scheduler:

```bash
# Get the source ID from the response above, then:
curl -s -X POST http://localhost/api/v1/sources/1/crawl \
  -H "Authorization: Bearer $TOKEN" | jq
```

Response:
```json
{"detail": "Crawl enqueued for source 1"}
```

Watch the worker pick it up:

```bash
make worker-logs
```

---

## 11. Search Findings

Once the crawler has run, search across all indexed content:

```bash
curl -s "http://localhost/api/v1/findings/search?q=acmecorp" \
  -H "Authorization: Bearer $TOKEN" | jq
```

The search runs against Elasticsearch with `multi_match` across the title, content, and matched keywords fields — with highlights returned so you can see exactly where the hit landed.

---

## 12. Configure Alert Delivery

Set up where alerts go when a keyword match is found:

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
```

---

## 13. Generate an API Key

For scripted access or SIEM integration, generate an API key tied to your user:

```bash
curl -s -X POST http://localhost/api/v1/auth/api-key \
  -H "Authorization: Bearer $TOKEN" | jq
```

Use it in subsequent requests with the `X-API-Key` header instead of Bearer:

```bash
curl -s http://localhost/api/v1/findings \
  -H "X-API-Key: your_api_key_here" | jq
```

Calling `POST /auth/api-key` again rotates the key — the old one is immediately invalidated.

---

## 14. Export Findings

Export all findings as a JSON file (suitable for SIEM ingestion or reporting):

```bash
curl -s -X POST http://localhost/api/v1/export/findings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}' \
  -o findings_export.json
```

To scope the export to a specific source or watchlist:

```bash
-d '{"format": "json", "source_id": 1}'
-d '{"format": "json", "watchlist_id": 1}'
```

---

## 15. Managing Users

All user management is done via direct DB access in v1 (a user management UI is on the roadmap).

Open a psql shell:

```bash
make shell-db
```

Create a read-only user (for analysts who shouldn't be modifying sources or watchlists):

```sql
INSERT INTO users (email, password_hash, role)
VALUES ('analyst@acmecorp.com', '<bcrypt_hash>', 'readonly');
```

Generate a bcrypt hash with Python:

```bash
docker compose exec backend python -c \
  "from passlib.context import CryptContext; \
   print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"
```

---

## 16. Day-to-Day Operations

**Restart everything:**
```bash
make restart
```

**Check crawler output:**
```bash
make worker-logs
```

**Run a one-off migration after a model change:**
```bash
make makemigration name="add_tags_to_watchlist"
make migrate
```

**Full interactive backend shell** (for debugging, running scripts):
```bash
make shell-backend
```

---

## 17. Stopping and Cleaning Up

Stop all containers (data volumes are preserved):

```bash
make down
```

To also wipe all data (destructive — drops all volumes):

```bash
docker compose down -v
```

---

## API Reference

Interactive API docs (Swagger UI) are available at:

```
http://localhost/api/v1/docs
```

ReDoc (read-only, better for sharing):

```
http://localhost/api/v1/redoc
```

Both are auto-generated from the FastAPI OpenAPI schema and stay in sync with the code.

---

## Troubleshooting

**Elasticsearch not healthy on startup**

Give it 90 seconds. If it still fails, check it has enough memory:
```bash
docker compose logs elasticsearch | grep -i error
```
Increase `ES_JAVA_OPTS` heap in `docker-compose.yml` if the host has more RAM available.

**`make migrate` fails with "could not connect to server"**

Postgres isn't ready yet. Run `make logs` and wait for `database system is ready to accept connections`, then retry.

**Tor check returns False**

The Tor container takes up to 60 seconds to bootstrap on first start. Wait and re-run `make tor-check`. If it still fails, the container may be blocked from reaching the Tor network — check your host firewall.

**JWT expired**

Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 480 = 8 hours). Log in again via `POST /auth/login`.
