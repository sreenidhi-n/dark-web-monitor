# Contributing to Dark Web Monitor

## Dev Environment Setup

1. Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) v2+.
2. Clone the repo and copy the example env file:
   ```bash
   cp .env.example .env
   ```
3. Generate a secret key and update `.env`:
   ```bash
   openssl rand -hex 32
   ```
4. Start all services:
   ```bash
   make up && make migrate
   ```
5. The dashboard is at `http://localhost`, the API at `http://localhost/api/v1/docs`.

For backend development with hot reload, the backend container already runs `uvicorn --reload` and mounts `./backend` as a volume.

---

## Submitting Pull Requests

- **One concern per PR.** Bug fix, feature, or refactor — not all three.
- **Tests required** for new crawler logic, router endpoints, and notification dispatch. Run `make test` before opening a PR.
- **Lint must pass.** Run `make lint`. We use `ruff` with default settings.
- Write a clear PR description: what changed and why, not just what the diff shows.
- For security-sensitive changes (auth, crawler, data handling), tag a maintainer for review before merging.

---

## Adding a New Crawler Adapter

A crawler adapter is responsible for scraping a specific type of `.onion` source (e.g., a forum with a particular structure, a paste site, a search index like Ahmia).

1. Create a new file in `backend/app/crawler/adapters/` (directory to be created in v0.2).
2. Implement the `BaseScraper` interface:
   ```python
   class BaseScraper:
       def can_handle(self, url: str) -> bool: ...
       def scrape(self, url: str, session: TorSession) -> list[dict]: ...
   ```
3. Register your adapter in `backend/app/crawler/registry.py`.
4. Add tests in `backend/tests/crawler/`.

Generic `.onion` scraping falls back to `OnionScraper` in `scraper.py`. Adapters are only needed for sites with structure worth parsing beyond plain text.

---

## Submitting New Source Lists

`.onion` URLs must **never** be hardcoded in source files. The reasons:
- Active `.onion` addresses change frequently and hardcoded lists go stale fast.
- Committing them creates a public record that could tip off operators of monitored services.
- Source lists are operator-specific — what's relevant to one org isn't to another.

**How to contribute source lists:**
- Open a GitHub Issue with the label `source-list` describing the category (e.g., "paste sites", "credential marketplaces", "forum directories") without including raw `.onion` URLs.
- Maintainers will review and add them to the database seed mechanism, which is gitignored.
- If you want to seed your own instance, edit `infra/seeds/sources.json.example` (forthcoming) and run `make seed`.

---

## Issue Templates

Use the following labels when opening issues:
- `bug` — something broken
- `feature` — new capability
- `crawler` — scraping / Tor connectivity
- `frontend` — UI/UX issues
- `source-list` — submitting new .onion sources to monitor
- `security` — report via private disclosure, not a public issue

---

## Code of Conduct

All contributors are expected to follow the project's Code of Conduct (forthcoming). The short version: be direct, be respectful, stay on topic.
