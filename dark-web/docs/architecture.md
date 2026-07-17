# Architecture

## System Diagram

```
┌─────────────────────────────────────────────────┐
│                   Browser                        │
└───────────────────┬─────────────────────────────┘
                    │ HTTP (port 80)
┌───────────────────▼─────────────────────────────┐
│                  Nginx                           │
│   /api/* → backend:8000   /* → frontend:3000     │
└──────────┬────────────────────────┬─────────────┘
           │                        │
┌──────────▼──────────┐  ┌──────────▼──────────────┐
│   FastAPI Backend   │  │   Next.js Frontend       │
│   (uvicorn, :8000)  │  │   (node, :3000)          │
└──────────┬──────────┘  └──────────────────────────┘
           │
     ┌─────┴──────────────────────────┐
     │                                │
┌────▼──────┐  ┌─────────┐  ┌────────▼──────────────┐
│ PostgreSQL│  │  Redis  │  │   Celery Workers        │
│  :5432    │  │  :6379  │  │   (worker + beat)       │
└───────────┘  └─────────┘  └──────────┬─────────────┘
                                        │
                             ┌──────────▼──────────────┐
                             │   Tor Proxy (dperson)    │
                             │   SOCKS5 :9050           │
                             │   HTTP (Privoxy) :8118   │
                             └──────────┬──────────────┘
                                        │ .onion
                                  ┌─────▼──────┐
                                  │  Dark Web   │
                                  └─────────────┘
                             ┌───────────────────────┐
                             │   Elasticsearch :9200  │
                             │   (findings index)     │
                             └───────────────────────┘
```

## Service Roles

**Nginx** — reverse proxy. Routes `/api/*` to the FastAPI backend and everything else to Next.js. Handles WebSocket upgrades for Next.js HMR in development.

**FastAPI backend** — REST API server. Handles auth (JWT), CRUD for sources/watchlists/findings/alerts, proxies search queries to Elasticsearch, and enqueues Celery tasks when a manual crawl is triggered.

**Next.js frontend** — React SPA. Dashboard with findings feed, source management, watchlist editor, and alert history. Communicates with the backend via `/api/v1/*`.

**PostgreSQL** — primary data store. Holds users, sources, findings (with content hashes for deduplication), watchlists, and alert records.

**Redis** — Celery broker and result backend. Also used for caching hot queries.

**Celery worker** — executes crawl tasks asynchronously so scraping never blocks the API process. Concurrency of 5 by default (each worker slot handles one `.onion` source at a time).

**Celery beat** — scheduler. Fires `crawl_all_sources` every hour; the task itself checks each source's `crawl_frequency_hours` to decide whether it's due.

**Tor proxy (dperson/torproxy)** — runs the Tor daemon (SOCKS5 on `:9050`) and Privoxy (HTTP on `:8118`). The crawler uses `socks5h://` so `.onion` DNS resolves through Tor, not the host.

**Elasticsearch** — full-text search index over finding content. Separate from PostgreSQL so search latency stays low as the findings table grows. Findings are indexed by content hash (idempotent).

## How a Crawl Works

1. **Trigger** — Celery beat fires `crawl_all_sources` every hour, or an analyst triggers an immediate crawl via `POST /api/v1/sources/{id}/crawl`.
2. **Task enqueue** — `crawl_source.delay(source_id)` is published to the Redis queue.
3. **Worker pickup** — a Celery worker dequeues the task and instantiates `TorSession` + `OnionScraper`.
4. **Circuit check** — every `CIRCUIT_ROTATE_EVERY` requests, `TorSession` signals the Tor control port to rotate the circuit (`stem` → `Signal.NEWNYM`).
5. **Scrape** — `OnionScraper.scrape(source.onion_url)` fetches the page through Tor, parses with BeautifulSoup/lxml, extracts title, text, and outbound links.
6. **Deduplication** — SHA-256 hash of the page text. If a Finding with this hash already exists, only `last_seen` is updated.
7. **Keyword matching** — `extract_keyword_matches(text, all_active_keywords)` runs against all active watchlists. Any match creates an Alert record.
8. **Elasticsearch indexing** — `index_finding()` upserts the document by content hash.
9. **Alert dispatch** — `dispatch_alert.delay(alert_id)` is enqueued for each new match. The dispatch task routes to email, Slack, or webhook based on the alert's channel config.
10. **Source update** — `source.last_crawled_at` is updated to now.
