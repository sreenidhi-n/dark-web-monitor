# Design Product Requirement (DPR)
## Dark Web Monitoring and Detection Tool
**Version:** 0.1  
**Date:** 2026-07-17  
**Status:** Draft

---

## 1. Executive Summary

An open-source, self-hosted dark web monitoring platform that alerts security teams when their organization's data, keywords, or assets surface on `.onion` services — filling a gap that commercial tools like Recorded Future and DarkOwl occupy at prohibitive cost.

---

## 2. Problem and Market Gap

The dark web hosts a continuous stream of credential leaks, data breach dumps, brand impersonation, and early-stage attack planning. Organizations that want proactive visibility into this have two options today:

- **Commercial platforms** (Recorded Future, DarkOwl, SpyCloud) — effective but expensive, closed-source, and SaaS-only.
- **DIY scripts** — fragile, unmaintained, no UI, no alerting.

There is no credible, actively maintained, self-hostable open-source tool in this space. This project is that tool.

---

## 3. Primary Persona

**SOC Analyst / Threat Intelligence Analyst** at a mid-size organization (50–5,000 employees).

- Has technical literacy to self-host a Docker Compose stack.
- Needs to monitor for credential leaks, brand mentions, and targeted attack discussions on dark web forums.
- Cannot justify a $50K/year commercial subscription but has a real, recurring need.
- Produces findings reports for a security manager or CISO.

**Secondary persona:** Independent security researchers and red team operators using the tool for OSINT in authorized engagements.

> **Note on LEAs:** Law enforcement agencies are a valid downstream user but cannot be the primary open-source adopter due to procurement, compliance, and operational security constraints. They will find this tool if it is good.

---

## 4. v1 Scope

### In scope for v1

| Module | Description |
|---|---|
| Keyword / domain watchlist | Define terms, domains, or emails to monitor |
| Tor crawler | Crawl `.onion` sources on a defined schedule |
| Search index | Elasticsearch-backed full-text search over findings |
| Alert system | Email, Slack, and webhook notifications on keyword match |
| Dashboard | Web UI: findings feed, search, watchlist management, alert config |
| Auth | Local user accounts with role-based access (admin / analyst / read-only) |
| Export | JSON and PDF export of findings for reporting |
| Self-hosted setup | Single `docker compose up` deployment |

### Explicitly out of scope for v1 (roadmap)

| Feature | Target version |
|---|---|
| Cryptocurrency transaction tracking | v2 |
| NLP-based user profiling | v2 |
| EXIF / image metadata analysis | v2 |
| Clearnet correlation mapping | v2 |
| SIEM / Splunk integration | v2 |
| Automated threat actor attribution | v3 |
| ML-based anomaly detection | v3 |

---

## 5. Technical Architecture

### Overview

A modular monorepo deployed via Docker Compose. All components are containerized and communicate internally. No cloud dependency — fully air-gappable.

```
┌─────────────────────────────────────────────────┐
│                   Browser                        │
└───────────────────┬─────────────────────────────┘
                    │ HTTPS
┌───────────────────▼─────────────────────────────┐
│              React Frontend (Next.js)            │
│         shadcn/ui · Recharts · TanStack Query    │
└───────────────────┬─────────────────────────────┘
                    │ REST / WebSocket
┌───────────────────▼─────────────────────────────┐
│              FastAPI Backend                     │
│         JWT Auth · RBAC · OpenAPI docs           │
└──────┬────────────┬──────────────┬──────────────┘
       │            │              │
┌──────▼──────┐ ┌───▼────┐ ┌──────▼──────────────┐
│  PostgreSQL │ │  Redis │ │   Celery Workers      │
│  (findings, │ │ (queue,│ │  (crawl jobs, alert  │
│  users,     │ │ cache) │ │   dispatch, indexing) │
│  watchlists)│ └────────┘ └──────────┬────────────┘
└─────────────┘                       │
                          ┌───────────▼────────────┐
                          │    Tor Proxy Layer      │
                          │  (stem + Privoxy +      │
                          │   requests[socks5])     │
                          └───────────┬────────────┘
                                      │
                          ┌───────────▼────────────┐
                          │   Elasticsearch         │
                          │   (full-text index      │
                          │    of findings)         │
                          └────────────────────────┘
```

### Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | Next.js + shadcn/ui + Recharts | Interactive UI; static matplotlib charts are insufficient for a monitoring product |
| Backend | FastAPI (Python) | Async-native; critical for concurrent crawl management; auto-generates OpenAPI docs |
| Task queue | Celery + Redis | Crawling cannot block the API process; scheduled jobs per source |
| Database | PostgreSQL | JSON support, triggers for alert conditions, robust full-text search |
| Search index | Elasticsearch | Fast keyword search across large finding sets |
| Tor connectivity | `stem` + `requests[socks5]` + Privoxy | Core mechanism for reaching `.onion` addresses — the most critical dependency |
| Notifications | SMTP + Slack webhooks | Alert delivery in v1 |
| Containerization | Docker + Docker Compose | Single-command self-hosted setup |

### Tor Connectivity

The crawler authenticates with a local Tor daemon via `stem`, rotates circuits between sources, and routes HTTP requests through a SOCKS5 proxy (Privoxy). Circuit rotation cadence is configurable per source to avoid detection patterns. Direct `.onion` DNS resolution is handled by Tor — no external DNS leaks.

**Dependencies:** `tor`, `stem`, `requests[socks5]`, `privoxy`

---

## 6. Data Model

### Core entities

**Source**
- `id`, `name`, `onion_url`, `crawl_frequency`, `last_crawled`, `active`
- Represents a `.onion` site or directory to monitor

**Finding**
- `id`, `source_id`, `url`, `title`, `content_snippet`, `full_content_hash`, `first_seen`, `last_seen`, `matched_keywords[]`
- Deduplicated by content hash; updated on re-detection

**Watchlist**
- `id`, `owner_id`, `name`, `keywords[]`, `domains[]`, `emails[]`, `created_at`
- Defines what to match against incoming findings

**Alert**
- `id`, `watchlist_id`, `finding_id`, `triggered_at`, `channel` (email/slack/webhook), `delivered`, `acknowledged`

**User**
- `id`, `email`, `password_hash`, `role` (admin/analyst/readonly), `api_key`, `created_at`

---

## 7. API Contract (Frontend ↔ Backend)

All endpoints under `/api/v1/`. Auth via Bearer JWT. Full OpenAPI spec auto-generated at `/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/login` | Obtain JWT |
| `GET` | `/findings` | Paginated findings feed (filterable by keyword, date, source) |
| `GET` | `/findings/{id}` | Full finding detail |
| `GET` | `/findings/search?q=` | Full-text search via Elasticsearch |
| `GET/POST` | `/watchlists` | List / create watchlists |
| `PUT/DELETE` | `/watchlists/{id}` | Update / remove watchlist |
| `GET/POST` | `/sources` | List / add `.onion` sources |
| `POST` | `/sources/{id}/crawl` | Trigger immediate crawl |
| `GET/POST` | `/alerts/config` | List / configure alert channels |
| `GET` | `/alerts/history` | Alert delivery history |
| `POST` | `/export/findings` | Export findings as JSON or PDF |
| `GET` | `/health` | Service health (for Docker healthcheck) |

---

## 8. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Setup time | `docker compose up` to working UI in under 5 minutes |
| Crawl concurrency | Minimum 5 simultaneous `.onion` sources |
| Search latency | Full-text search results in under 2 seconds for up to 1M findings |
| Alert latency | Notification delivered within 60 seconds of a keyword match being indexed |
| Data retention | Configurable; default 90 days, no hard cap |
| Air-gap compatible | All runtime dependencies resolvable without outbound internet (except Tor) |
| API key support | Every user action available via API key for SIEM/scripted integration |
| Self-hosted only | No telemetry, no call-home, no cloud dependency |

---

## 9. Limitations, Risks, and Legal

### Technical limitations

- **Tor reliability:** Circuit availability and latency are outside the tool's control. Sources may be intermittently unreachable.
- **Scraping resistance:** Some `.onion` forums require registration or solve CAPTCHAs. These cannot be crawled automatically.
- **Evolving targets:** `.onion` addresses change frequently. Source lists require ongoing maintenance by the operator.
- **No guarantee of coverage:** This tool indexes what it can reach. Absence of a finding does not mean absence of exposure.
- **External API dependency (v2+):** Cryptocurrency tracking will rely on blockchain explorer APIs subject to rate limits and policy changes.

### Legal and ethical use

This tool is designed for **authorized defensive security operations only.**

Operators are responsible for ensuring their use complies with applicable law, including but not limited to:
- Computer Fraud and Abuse Act (CFAA) — United States
- Computer Misuse Act — United Kingdom
- Relevant data protection regulations (GDPR, CCPA) regarding handling of any PII discovered

**This tool must not be used to:**
- Access systems or services without authorization
- Conduct surveillance of individuals outside of an authorized investigation
- Facilitate any illegal activity

A `LEGAL.md` and `CODE_OF_CONDUCT.md` will accompany the repository at launch.

---

## 10. Open-Source Positioning

### License

**AGPL-3.0** — requires any SaaS deployment or fork to open-source their modifications. Keeps the project free for self-hosters while preventing commercial free-riding.

### Repository structure (planned)

```
dark-web-monitor/
├── backend/          # FastAPI app, Celery workers, crawler modules
├── frontend/         # Next.js app
├── infra/            # Docker Compose, Nginx config, env templates
├── docs/             # Architecture diagrams, user guide, API reference
├── DPR.md            # This document
├── LEGAL.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
└── README.md
```

### Contributing

A `CONTRIBUTING.md` will define:
- Dev environment setup (local Docker Compose)
- Module ownership and where to add new crawler adapters
- PR standards and issue templates
- How to submit new `.onion` source lists safely

### Roadmap

| Version | Focus |
|---|---|
| v0.1 | Repo scaffold, Docker Compose, CI pipeline |
| v0.2 | Tor crawler + Elasticsearch indexing |
| v0.3 | FastAPI backend + auth |
| v0.4 | React dashboard + alerting |
| v1.0 | Full v1 feature-complete, public release |
| v2.0 | Crypto tracking, NLP user profiling, SIEM integration |
| v3.0 | ML anomaly detection, threat actor attribution |
