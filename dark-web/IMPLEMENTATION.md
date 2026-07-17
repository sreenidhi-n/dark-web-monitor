# Implementation Log

Track of everything built so far, what's fully implemented vs stubbed, and what's next.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Fully implemented |
| 🔧 | Stubbed — structure and signatures in place, body is TODO |
| 📋 | Planned, not started |

---

## Infrastructure & Config

| File | Status | Notes |
|---|---|---|
| `docker-compose.yml` | ✅ | 8 services: postgres, redis, elasticsearch, tor, backend, worker, beat, frontend, nginx |
| `.env.example` | ✅ | All config vars documented with inline comments |
| `.gitignore` | ✅ | Python, Node, Docker, security-sensitive paths (tor keys, exports, PII) |
| `Makefile` | ✅ | up, down, build, restart, logs, worker-logs, shell-backend, shell-db, migrate, makemigration, create-admin, test, lint, tor-check |
| `infra/nginx/nginx.conf` | ✅ | Reverse proxy: /api/* → backend, /* → frontend, WebSocket upgrade headers |
| `infra/tor/torrc.example` | ✅ | Template for standalone Tor daemon (Docker image manages its own) |
| `infra/privoxy/config.example` | ✅ | HTTP→SOCKS5 bridge template |

---

## Documentation

| File | Status | Notes |
|---|---|---|
| `DPR.md` | ✅ | Full rewritten Design Product Requirement — v1 scope, stack, data model, API contract, legal |
| `README.md` | ✅ | Quickstart, tech stack, project structure, roadmap |
| `LEGAL.md` | ✅ | CFAA, Computer Misuse Act, GDPR/CCPA, prohibited uses |
| `CONTRIBUTING.md` | ✅ | Dev setup, PR standards, how to add crawlers, source list policy |
| `docs/architecture.md` | ✅ | ASCII system diagram, service roles, crawl pipeline walkthrough |
| `docs/walkthrough.md` | ✅ | End-to-end user guide |

---

## Backend

### Core Setup

| File | Status | Notes |
|---|---|---|
| `backend/Dockerfile` | ✅ | Python 3.12 slim, installs system deps (gcc, libpq-dev) |
| `backend/requirements.txt` | ✅ | FastAPI, SQLAlchemy async, Celery, Elasticsearch, stem, BeautifulSoup, aiosmtplib, httpx |
| `backend/app/config.py` | ✅ | Pydantic Settings — all env vars, singleton `settings` export |
| `backend/app/database.py` | ✅ | Async SQLAlchemy engine, `AsyncSessionLocal`, `Base`, `get_db` dependency |
| `backend/app/main.py` | ✅ | FastAPI app, lifespan (ES index on startup), CORS, all routers mounted at `/api/v1` |

### Models (SQLAlchemy 2.0)

| Model | Status | Notes |
|---|---|---|
| `User` | ✅ | id, email, password_hash, role (enum), api_key, is_active, created_at |
| `Source` | ✅ | id, name, onion_url, crawl_frequency_hours, last_crawled_at, is_active, created_by_id FK |
| `Finding` | ✅ | id, source_id FK, url, title, content_snippet, content_hash (SHA-256, unique), matched_keywords (JSON), first_seen, last_seen |
| `Watchlist` | ✅ | id, name, owner_id FK, keywords/domains/emails (JSON arrays), is_active |
| `Alert` | ✅ | id, watchlist_id FK, finding_id FK, triggered_at, channel (enum), delivered, acknowledged, acknowledged_at |
| `AlertConfig` | ✅ | id, watchlist_id FK, channel (enum), destination (email/webhook URL), is_active |

### Migrations (Alembic)

| File | Status | Notes |
|---|---|---|
| `alembic.ini` | ✅ | URL set from settings at runtime — never hardcoded |
| `alembic/env.py` | ✅ | Async engine (`NullPool`), imports all models for autogenerate |
| `alembic/script.py.mako` | ✅ | Migration file template |
| `alembic/versions/0001_initial_schema.py` | ✅ | Creates all 5 tables + 2 enums in FK dependency order; full downgrade |
| `alembic/versions/0002_add_alert_configs.py` | ✅ | Adds `alert_configs` table |

### Auth Router (`/api/v1/auth`)

| Endpoint | Status | Notes |
|---|---|---|
| `POST /login` | ✅ | OAuth2 password form, bcrypt verify, returns signed JWT |
| `POST /logout` | ✅ | Stateless acknowledge (client drops token) |
| `GET /me` | ✅ | Returns current user from JWT or API key |
| `POST /api-key` | ✅ | Generates/rotates `X-API-Key` for authenticated user |
| `get_current_user` dep | ✅ | Dual-scheme: Bearer JWT → X-API-Key fallback |
| `require_role()` dep | ✅ | Role-based access control factory for use in any router |

### Findings Router (`/api/v1/findings`)

| Endpoint | Status | Notes |
|---|---|---|
| `GET /` | ✅ | Paginated, filterable by source_id / keyword (JSON @> containment) / since |
| `GET /search` | ✅ | ES multi_match with highlights; returns typed `SearchHit` list |
| `GET /{id}` | ✅ | DB fetch with 404 |

### Sources Router (`/api/v1/sources`)

| Endpoint | Status | Notes |
|---|---|---|
| `GET /` | ✅ | `active_only` query param; ordered newest-first |
| `POST /` | ✅ | `.onion` URL validation, duplicate → 409, sets `created_by_id` |
| `GET /{id}` | ✅ | 404 on missing |
| `PUT /{id}` | ✅ | Full replacement; duplicate URL → 409 |
| `DELETE /{id}` | ✅ | Soft-delete; admin only |
| `POST /{id}/crawl` | ✅ | Validates source exists + is active before enqueuing |

### Watchlists Router (`/api/v1/watchlists`)

| Endpoint | Status | Notes |
|---|---|---|
| `GET /` | ✅ | Owner-scoped (admins see all); active only |
| `POST /` | ✅ | Strips + deduplicates keywords/domains/emails; admin/analyst only |
| `GET /{id}` | ✅ | Ownership check (owner or admin) |
| `PUT /{id}` | ✅ | Ownership check; updates all term lists |
| `DELETE /{id}` | ✅ | Soft-delete; ownership check |

### Alerts Router (`/api/v1/alerts`)

| Endpoint | Status | Notes |
|---|---|---|
| `GET /config` | ✅ | Scoped to current user's watchlists |
| `POST /config` | ✅ | Validates watchlist ownership before creating |
| `DELETE /config/{id}` | ✅ | Soft-delete with ownership check |
| `GET /history` | ✅ | Paginated, filterable by watchlist_id / delivered / acknowledged |
| `POST /history/{id}/acknowledge` | ✅ | Marks alert acknowledged with timestamp; ownership check |

### Export Router (`/api/v1/export`)

| Endpoint | Status | Notes |
|---|---|---|
| `POST /findings` | ✅ | JSON export with source_id + since filters; proper Content-Disposition header; PDF → 501 |

### Crawler

| File | Status | Notes |
|---|---|---|
| `crawler/tor_session.py` | ✅ | TorSession: Tor Browser UA, circuit rotation via stem, verify_tor(), get/post |
| `crawler/scraper.py` | ✅ | OnionScraper: BS4/lxml parse, keyword matching, SHA-256 hash, link extraction |
| `crawler/scheduler.py` | ✅ | Full pipeline: scrape → deduplicate → match watchlists → create Alerts → ES index → dispatch_alert; exponential backoff retry |

### Search

| File | Status | Notes |
|---|---|---|
| `search/client.py` | ✅ | `get_es_client`, `ensure_index` (with mapping), `index_finding`, `search_findings` (multi_match + highlights) |

### Notifications

| File | Status | Notes |
|---|---|---|
| `notifications/email.py` | ✅ | `send_alert_email` via aiosmtplib + STARTTLS |
| `notifications/slack.py` | ✅ | `send_slack_alert` via httpx POST to webhook URL |
| `notifications/webhook.py` | ✅ | `send_webhook_alert` via httpx POST, generic JSON payload |

### Scripts

| File | Status | Notes |
|---|---|---|
| `scripts/create_admin.py` | ✅ | Idempotent admin bootstrap; called via `make create-admin` |

---

## Frontend

| File | Status | Notes |
|---|---|---|
| `frontend/Dockerfile` | ✅ | Multi-stage: deps → builder → runner (standalone Next.js output) |
| `frontend/package.json` | ✅ | Next.js 14, TanStack Query, Recharts, Lucide, Tailwind |
| `frontend/next.config.js` | ✅ | Standalone output, `/api/*` rewrite to backend |
| `frontend/tsconfig.json` | ✅ | Strict, `@/*` path alias |
| `frontend/tailwind.config.ts` | ✅ | Dark theme base colors |
| `src/app/globals.css` | ✅ | Tailwind directives |
| `src/app/layout.tsx` | ✅ | Root layout: Inter font, QueryClientProvider, top nav |
| `src/app/page.tsx` | ✅ | Dashboard: 4 stat cards (findings, sources, watchlists, today's alerts), 7-day bar chart |
| `src/lib/api.ts` | ✅ | Full typed fetch client: dual-auth (JWT + X-API-Key), all CRUD + search + alert endpoints, 204 handling |
| `src/lib/types.ts` | ✅ | TypeScript types for all 6 data models + enums + SearchHit + FindingsPage |
| `src/lib/utils.ts` | ✅ | `cn()` (clsx + tailwind-merge), `formatRelative()`, `truncate()` |

### UI Components (`src/components/ui/`)

| Component | Status | Notes |
|---|---|---|
| `Button.tsx` | ✅ | Variants: primary / secondary / ghost; sizes: sm / md; `loading` prop spins a Spinner |
| `Badge.tsx` | ✅ | Variants: default / success / danger / warning / info |
| `Spinner.tsx` | ✅ | Sizes: sm / md / lg; animated SVG ring |
| `Modal.tsx` | ✅ | Portal via `createPortal`, Escape + backdrop close, focus trap |
| `EmptyState.tsx` | ✅ | Icon + title + description + optional CTA `action` prop |
| `Pagination.tsx` | ✅ | Prev/Next with `page`, `pageSize`, `total` props |
| `TagInput.tsx` | ✅ | Enter/comma to add, Backspace to remove last, auto-deduplicates |

### Pages

| Page | Status | Notes |
|---|---|---|
| `app/page.tsx` (Dashboard) | ✅ | 4 stat cards + 7-day findings bar chart (Recharts) |
| `app/findings/page.tsx` | ✅ | Browse mode (paginated + source/date filters) and ES search mode (350ms debounce); expandable FindingCard + SearchHitCard with highlights |
| `app/sources/page.tsx` | ✅ | Table with per-source crawl loading state; Create/Edit modal with .onion validation; soft delete |
| `app/watchlists/page.tsx` | ✅ | Card grid with TagInput for keywords/domains/emails; +N overflow badges; Create/Edit/Delete |
| `app/alerts/page.tsx` | ✅ | Tab layout (Alert History / Notification Config); acknowledge button; Add Config modal with dynamic destination placeholder |

---

## What's Next

1. **PDF export** — reportlab or weasyprint integration (currently returns 501)
2. **Tests** — pytest suite for routers and crawler modules
