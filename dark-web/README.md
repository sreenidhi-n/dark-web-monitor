# Dark Web Monitor

A self-hosted, open-source dark web monitoring platform. Define keyword watchlists, crawl `.onion` sources on a schedule, and get alerted when your organization's data surfaces somewhere it shouldn't.

Built for SOC analysts and threat intelligence teams who need proactive dark web visibility without a $50K/year commercial subscription.

---

## Features (v1)

- **Keyword & domain watchlists** — monitor for credentials, emails, domains, brand terms
- **Tor crawler** — automated `.onion` scraping with circuit rotation via `stem`
- **Full-text search** — Elasticsearch-backed search across all findings
- **Real-time alerting** — email, Slack, and webhook notifications on keyword match
- **Web dashboard** — findings feed, source management, watchlist editor, alert history
- **RBAC** — admin / analyst / read-only roles with API key support
- **JSON export** — findings export for reporting and SIEM handoff
- **Single-command setup** — `docker compose up` and you're running

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, Recharts, TanStack Query |
| Backend | FastAPI (Python 3.12), SQLAlchemy 2.0 async |
| Task queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Search | Elasticsearch 8 |
| Tor connectivity | `stem` + `requests[socks5]` + dperson/torproxy |
| Reverse proxy | Nginx |
| Containerization | Docker Compose |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2+
- 4 GB RAM minimum (Elasticsearch is the hungry one)

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/your-handle/dark-web-monitor.git
cd dark-web-monitor

# 2. Copy and edit config
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY
# Generate SECRET_KEY with: openssl rand -hex 32

# 3. Start everything
make up

# 4. Run migrations
make migrate

# 5. Open the dashboard
open http://localhost
```

First-time startup takes ~60 seconds for Elasticsearch to become healthy.

To verify Tor is routing correctly:
```bash
make tor-check
```

---

## Project Structure

```
dark-web-monitor/
├── backend/          # FastAPI app, Celery workers, crawler modules
│   └── app/
│       ├── crawler/      # Tor session, scraper, Celery scheduler
│       ├── models/       # SQLAlchemy models
│       ├── routers/      # FastAPI route handlers
│       ├── search/       # Elasticsearch client
│       ├── notifications/ # Email, Slack, webhook dispatch
│       ├── config.py
│       ├── database.py
│       └── main.py
├── frontend/         # Next.js app
├── infra/            # Nginx config, Tor/Privoxy templates
├── docs/             # Architecture, dev guide
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## Roadmap

| Version | Focus |
|---|---|
| v0.1 | Repo scaffold, Docker Compose, CI |
| v0.2 | Tor crawler + Elasticsearch indexing |
| v0.3 | FastAPI backend + auth |
| v0.4 | React dashboard + alerting |
| **v1.0** | **Full feature-complete, public release** |
| v2.0 | Crypto transaction tracking, NLP user profiling, SIEM integration |
| v3.0 | ML anomaly detection, threat actor attribution |

---

## Legal

This tool is for **authorized defensive security operations only.** Read [LEGAL.md](LEGAL.md) before use.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[AGPL-3.0](LICENSE)
