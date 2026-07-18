import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from celery import Celery
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.alert import Alert, AlertChannel
from app.models.alert_config import AlertConfig
from app.models.finding import Finding
from app.models.source import Source
from app.models.watchlist import Watchlist, ThreatCategory, CATEGORY_SEVERITY
from app.notifications.email import send_alert_email
from app.notifications.slack import send_slack_alert
from app.notifications.webhook import send_webhook_alert
from app.search.client import get_es_client, index_finding

logger = logging.getLogger(__name__)

# ── Celery app ────────────────────────────────────────────────────────────────

celery_app = Celery("dwm", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # Every hour beat checks all sources; per-source frequency is enforced inside the task.
        "crawl-all-active-sources": {
            "task": "app.crawler.scheduler.crawl_all_sources",
            "schedule": 3600.0,
        },
    },
)

# ── Worker-process DB singleton ───────────────────────────────────────────────
# Created once per Celery worker process, not once per task.

_engine = None
_session_factory: async_sessionmaker | None = None


def _get_session_factory() -> async_sessionmaker:
    global _engine, _session_factory
    if _session_factory is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def _db():
    async with _get_session_factory()() as session:
        yield session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_es_doc(finding: Finding, full_text: str) -> dict:
    return {
        "url": finding.url,
        "title": finding.title or "",
        "text": full_text,
        "matched_keywords": finding.matched_keywords,
        "source_id": finding.source_id,
        "content_hash": finding.content_hash,
        "first_seen": finding.first_seen.isoformat(),
        "last_seen": finding.last_seen.isoformat(),
    }


def _build_alert_text(wl_name: str, finding: Finding) -> str:
    keywords = ", ".join(finding.matched_keywords) or "—"
    return (
        f"[Dark Web Monitor] Match on watchlist '{wl_name}'\n"
        f"URL: {finding.url}\n"
        f"Matched terms: {keywords}\n"
        f"First seen: {finding.first_seen.isoformat()}"
    )


# ── Async pipeline implementations ───────────────────────────────────────────

async def _crawl_source_async(source_id: int) -> dict:
    from app.crawler.scraper import OnionScraper
    from app.crawler.tor_session import TorSession

    # ── 1. Load source ────────────────────────────────────────────────────────
    async with _db() as db:
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()
        if not source or not source.is_active:
            logger.warning("crawl_source: source %s not found or inactive", source_id)
            return {"source_id": source_id, "status": "skipped"}

        onion_url = source.onion_url

    # ── 2. Scrape (outside DB session — network I/O can be slow) ─────────────
    tor = TorSession()
    scraper = OnionScraper(tor)
    scraped = scraper.scrape(onion_url)

    async with _db() as db:
        # Reload source in this session for updating
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()

        if scraped.get("error"):
            logger.warning("Scrape error for source %s: %s", source_id, scraped["error"])
            source.last_crawled_at = datetime.now(timezone.utc)
            await db.commit()
            return {"source_id": source_id, "status": "scrape_error", "error": scraped["error"]}

        content_hash = scraped["content_hash"]
        now = datetime.now(timezone.utc)

        # ── 3. Deduplication ─────────────────────────────────────────────────
        dup = await db.execute(select(Finding).where(Finding.content_hash == content_hash))
        existing = dup.scalar_one_or_none()

        if existing:
            existing.last_seen = now
            source.last_crawled_at = now
            await db.commit()
            logger.debug("Duplicate finding for source %s (hash %s)", source_id, content_hash[:8])
            # Re-index in ES to keep last_seen fresh
            es = get_es_client()
            try:
                await index_finding(es, _build_es_doc(existing, scraped["text"]))
            finally:
                await es.close()
            return {"source_id": source_id, "status": "duplicate", "finding_id": existing.id}

        # ── 4. Match watchlists ──────────────────────────────────────────────
        wl_result = await db.execute(select(Watchlist).where(Watchlist.is_active.is_(True)))
        watchlists = wl_result.scalars().all()

        all_matched: list[str] = []
        wl_matches: list[tuple[Watchlist, list[str]]] = []
        matched_categories: list[ThreatCategory] = []

        for wl in watchlists:
            terms = wl.keywords + wl.domains + wl.emails
            matched = scraper.extract_keyword_matches(scraped["text"], terms)
            if matched:
                wl_matches.append((wl, matched))
                all_matched.extend(matched)
                try:
                    matched_categories.append(ThreatCategory(wl.category))
                except ValueError:
                    matched_categories.append(ThreatCategory.GENERAL)

        # Derive severity from the most severe matched category
        severity_order = ["critical", "high", "medium", "low"]
        candidate_severities = [CATEGORY_SEVERITY.get(c, "low") for c in matched_categories]
        severity = min(candidate_severities, key=lambda s: severity_order.index(s)) if candidate_severities else "low"

        # CSAM: never store content — only URL + hash for dedup and audit trail
        is_csam = ThreatCategory.CSAM in matched_categories
        if is_csam:
            content_snippet = "[CONTENT WITHHELD — POTENTIAL CSAM INDICATOR]"
            severity = "critical"
            logger.critical(
                "CSAM INDICATOR DETECTED — source=%s url=%s hash=%s keywords=%s",
                source_id, scraped["url"], content_hash[:16], all_matched,
            )
        else:
            content_snippet = scraped["snippet"]

        # ── 5. Create Finding ────────────────────────────────────────────────
        finding = Finding(
            source_id=source_id,
            url=scraped["url"],
            title=scraped.get("title") or None,
            content_snippet=content_snippet,
            content_hash=content_hash,
            matched_keywords=list(set(all_matched)),
            severity=severity,
            first_seen=now,
            last_seen=now,
        )
        db.add(finding)

        try:
            await db.flush()  # populate finding.id before creating alerts
        except IntegrityError:
            # Another worker indexed the same hash in a race — harmless, skip
            await db.rollback()
            logger.info("Hash race condition for source %s — skipping", source_id)
            return {"source_id": source_id, "status": "duplicate_race"}

        # ── 6. Create one Alert per AlertConfig per matched watchlist ─────────
        alert_dispatch: list[tuple[int, int]] = []  # (alert_id, config_id)

        for wl, _ in wl_matches:
            cfg_result = await db.execute(
                select(AlertConfig).where(
                    AlertConfig.watchlist_id == wl.id,
                    AlertConfig.is_active.is_(True),
                )
            )
            for config in cfg_result.scalars().all():
                alert = Alert(
                    watchlist_id=wl.id,
                    finding_id=finding.id,
                    channel=config.channel,
                    delivered=False,
                    acknowledged=False,
                )
                db.add(alert)
                await db.flush()
                alert_dispatch.append((alert.id, config.id))

        source.last_crawled_at = now
        await db.commit()
        finding_id = finding.id

    # ── 7. Index in Elasticsearch ─────────────────────────────────────────────
    es = get_es_client()
    try:
        await index_finding(es, _build_es_doc(finding, scraped["text"]))
    except Exception as exc:
        logger.error("ES indexing failed for finding %s: %s", finding_id, exc)
    finally:
        await es.close()

    # ── 8. Dispatch alert tasks ───────────────────────────────────────────────
    for alert_id, config_id in alert_dispatch:
        dispatch_alert.delay(alert_id, config_id)

    logger.info(
        "source=%s new finding=%s alerts=%d keywords=%s",
        source_id,
        finding_id,
        len(alert_dispatch),
        all_matched,
    )
    return {
        "source_id": source_id,
        "status": "ok",
        "finding_id": finding_id,
        "alerts_triggered": len(alert_dispatch),
    }


async def _crawl_all_sources_async() -> int:
    now = datetime.now(timezone.utc)
    async with _db() as db:
        result = await db.execute(select(Source).where(Source.is_active.is_(True)))
        sources = result.scalars().all()

    scheduled = 0
    for source in sources:
        if source.last_crawled_at is None:
            crawl_source.delay(source.id)
            scheduled += 1
        else:
            next_due = source.last_crawled_at + timedelta(hours=source.crawl_frequency_hours)
            if next_due <= now:
                crawl_source.delay(source.id)
                scheduled += 1

    logger.info("crawl_all_sources: scheduled %d of %d sources", scheduled, len(sources))
    return scheduled


async def _dispatch_alert_async(alert_id: int, config_id: int) -> None:
    async with _db() as db:
        alert_row = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = alert_row.scalar_one_or_none()
        if not alert:
            logger.error("dispatch_alert: alert %d not found", alert_id)
            return

        config_row = await db.execute(select(AlertConfig).where(AlertConfig.id == config_id))
        config = config_row.scalar_one_or_none()
        if not config:
            logger.error("dispatch_alert: config %d not found", config_id)
            return

        finding_row = await db.execute(select(Finding).where(Finding.id == alert.finding_id))
        finding = finding_row.scalar_one_or_none()

        wl_row = await db.execute(select(Watchlist).where(Watchlist.id == alert.watchlist_id))
        watchlist = wl_row.scalar_one_or_none()

        wl_name = watchlist.name if watchlist else "Unknown Watchlist"
        text_msg = _build_alert_text(wl_name, finding) if finding else f"[DWM] Alert for watchlist '{wl_name}'"

        webhook_payload = {
            "alert_id": alert_id,
            "watchlist": wl_name,
            "finding_url": finding.url if finding else None,
            "matched_keywords": finding.matched_keywords if finding else [],
            "first_seen": finding.first_seen.isoformat() if finding else None,
            "channel": config.channel.value,
        }

        delivered = False
        try:
            if config.channel == AlertChannel.email:
                delivered = await send_alert_email(
                    to=config.destination,
                    subject=f"[DWM Alert] {wl_name}",
                    body=text_msg,
                )
            elif config.channel == AlertChannel.slack:
                delivered = await send_slack_alert(text=text_msg, webhook_url=config.destination)
            elif config.channel == AlertChannel.webhook:
                delivered = await send_webhook_alert(payload=webhook_payload, webhook_url=config.destination)
        except Exception as exc:
            logger.error("Alert %d delivery failed: %s", alert_id, exc)

        alert.delivered = delivered
        await db.commit()

    logger.info("alert=%d channel=%s delivered=%s", alert_id, config.channel, delivered)


# ── Celery task wrappers ──────────────────────────────────────────────────────

@celery_app.task(name="app.crawler.scheduler.crawl_source", bind=True, max_retries=3)
def crawl_source(self, source_id: int) -> dict:
    """Crawl a single .onion source, index findings, and dispatch alerts."""
    try:
        return asyncio.run(_crawl_source_async(source_id))
    except Exception as exc:
        logger.error("crawl_source %s failed: %s", source_id, exc)
        # Exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@celery_app.task(name="app.crawler.scheduler.crawl_all_sources")
def crawl_all_sources() -> int:
    """Enqueue crawl tasks for all active sources that are due."""
    return asyncio.run(_crawl_all_sources_async())


@celery_app.task(name="app.crawler.scheduler.dispatch_alert", max_retries=5)
def dispatch_alert(alert_id: int, config_id: int) -> None:
    """Deliver a triggered alert via its configured channel."""
    asyncio.run(_dispatch_alert_async(alert_id, config_id))
