"""
Seed the database and Elasticsearch with realistic demo findings.

Usage:
    docker compose exec backend python scripts/seed_demo.py
"""
import asyncio
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from random import choice, randint

sys.path.insert(0, "/app")

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.finding import Finding
from app.models.source import Source
from app.models.watchlist import Watchlist
from app.models.alert import Alert, AlertChannel
from app.models.alert_config import AlertConfig
from app.search.client import get_es_client, index_finding

# ── Demo sources ──────────────────────────────────────────────────────────────

SOURCES = [
    {"name": "BreachForums Mirror",       "onion_url": "http://breachforumsukll3457.onion"},
    {"name": "RaidForums Archive",        "onion_url": "http://raidforumsl2xyz9873.onion"},
    {"name": "Dark Market Listings",      "onion_url": "http://darkmarket3fg8abc.onion"},
    {"name": "LeakBase Underground",      "onion_url": "http://leakbasexy5d62abc.onion"},
    {"name": "Exploit.in Mirror",         "onion_url": "http://exploitin9xyz1234.onion"},
]

# ── Demo findings ──────────────────────────────────────────────────────────────

now = datetime.now(timezone.utc)

FINDINGS = [
    {
        "source_idx": 0,
        "url": "http://breachforumsukll3457.onion/thread/18291",
        "title": "[FREE] Acme Corp Employee Database - 12K records",
        "text": (
            "Sharing full employee database dump from acme-corp.com internal HR system. "
            "Contains: full name, email, password hash (bcrypt), department, salary info. "
            "Leaked from insider — 12,847 records. Many accounts still active as of last week. "
            "Emails follow pattern firstname.lastname@acme-corp.com — easy for phishing. "
            "Download link in replies. Keywords: acme-corp employee leak HR salary passwords"
        ),
        "keywords": ["acme-corp.com", "acme-corp", "employee", "salary"],
        "days_ago": 2,
    },
    {
        "source_idx": 0,
        "url": "http://breachforumsukll3457.onion/thread/18105",
        "title": "COMBO LIST — 850K stealer logs EU/US mixed",
        "text": (
            "Fresh stealer logs from Redline and Raccoon campaigns. Over 850,000 unique credentials "
            "including banking logins, email accounts, crypto wallets, and corporate VPN credentials. "
            "Format: url:username:password. Includes hits from acme-corp.com VPN portal. "
            "Filtering available. Price: 0.08 BTC for full list, 0.01 BTC for corporate-only subset."
        ),
        "keywords": ["acme-corp.com", "credentials", "VPN"],
        "days_ago": 5,
    },
    {
        "source_idx": 1,
        "url": "http://raidforumsl2xyz9873.onion/post/44021",
        "title": "Database: globex.io — 2.3M users + plain passwords",
        "text": (
            "Dumped from globex.io — 2.3 million user records. "
            "Columns: user_id, username, email, password (MD5, easily cracked), "
            "registration_date, last_login, ip_address. "
            "Already cracked ~40%% of hashes. Contact for bulk pricing. "
            "Sample: user@globex.io:password123 (verified working)"
        ),
        "keywords": ["globex.io"],
        "days_ago": 8,
    },
    {
        "source_idx": 2,
        "url": "http://darkmarket3fg8abc.onion/listing/8834",
        "title": "[SELLING] C-suite email access — Fortune 500 company",
        "text": (
            "Selling persistent access to email accounts of senior executives at a Fortune 500 company. "
            "Includes CEO, CFO, and 3x VPs. Full inbox read/write via compromised mail server. "
            "Company operates in healthcare sector. Asking 2 BTC. "
            "Proof: can forward any recent email on demand. Valid for at least 30 days guaranteed."
        ),
        "keywords": ["email access", "C-suite", "executives"],
        "days_ago": 1,
    },
    {
        "source_idx": 3,
        "url": "http://leakbasexy5d62abc.onion/leaks/us-corporate-q2-2026",
        "title": "US Corporate Credential Dump — Q2 2026 Collection",
        "text": (
            "Aggregated corporate credential collection from Q2 2026 breaches. "
            "Includes hits from: acme-corp.com, techcorp.net, innovatehere.co, startupxyz.io. "
            "Total: 430K corporate email/password pairs across 200+ companies. "
            "Plaintext passwords where available, bcrypt hashes for the rest. "
            "Contains john.doe@acme-corp.com:Summer2024!, jane.smith@acme-corp.com:Welcome1 among others."
        ),
        "keywords": ["acme-corp.com", "john.doe@acme-corp.com", "corporate", "credentials"],
        "days_ago": 3,
    },
    {
        "source_idx": 3,
        "url": "http://leakbasexy5d62abc.onion/leaks/healthcare-2026",
        "title": "Healthcare Sector Data Leak — Patient PII",
        "text": (
            "Patient records from multiple US healthcare providers. Contains: "
            "full name, DOB, SSN, insurance ID, diagnosis codes, address. "
            "~180,000 records. Source: ransomware exfil. "
            "Contact for sample verification. Warning: HIPAA data — use at own risk."
        ),
        "keywords": ["healthcare", "SSN", "patient records"],
        "days_ago": 12,
    },
    {
        "source_idx": 4,
        "url": "http://exploitin9xyz1234.onion/forum/post/92331",
        "title": "Verified 0-day: Apache HTTPD RCE (unpatched)",
        "text": (
            "Selling working PoC for unauthenticated RCE in Apache HTTPD 2.4.58. "
            "Tested on Ubuntu 22.04 and Debian 12. Reliable one-shot shell via "
            "malformed Range header. No auth required. "
            "Shodan confirms 840K+ exposed instances. Starting bid: 5 BTC. "
            "Will auction to highest bidder by end of week."
        ),
        "keywords": ["0-day", "RCE", "Apache", "exploit"],
        "days_ago": 6,
    },
    {
        "source_idx": 4,
        "url": "http://exploitin9xyz1234.onion/forum/post/88210",
        "title": "Source code leak: internal fintech platform",
        "text": (
            "Leaked source code of a US fintech startup's trading platform. "
            "Includes: AWS credentials hardcoded in config files, "
            "private API keys for payment processor, "
            "JWT secret key (still active), full database schema. "
            "Company: PayFlow Inc. Repo size: ~1.2GB. "
            "Verified against live endpoints — still working."
        ),
        "keywords": ["AWS credentials", "API keys", "source code", "JWT"],
        "days_ago": 10,
    },
    {
        "source_idx": 0,
        "url": "http://breachforumsukll3457.onion/thread/17009",
        "title": "Stealer log hit: acme-corp.com VPN + internal wiki",
        "text": (
            "Got a hit in latest stealer campaign. Verified credentials: "
            "vpn.acme-corp.com — username: mwilson, password: Autumn2025! (working) "
            "intranet.acme-corp.com — same creds valid. "
            "Includes session cookie for their Confluence wiki. "
            "Can provide screenshot proof. Selling for 0.05 BTC."
        ),
        "keywords": ["acme-corp.com", "vpn.acme-corp.com", "intranet.acme-corp.com", "mwilson"],
        "days_ago": 0,
    },
    {
        "source_idx": 1,
        "url": "http://raidforumsl2xyz9873.onion/post/51983",
        "title": "Full credit card dump — 220K cards EU issuer",
        "text": (
            "220,000 credit card records from EU bank breach. "
            "Format: PAN|exp|CVV|name|billing_address|bank. "
            "All Visa/Mastercard. Validity rate ~65%% (checked sample). "
            "Price: $5 per card, bulk discount available. "
            "Cards from 2024-2026, most expire 2027+."
        ),
        "keywords": ["credit card", "CVV", "carding"],
        "days_ago": 15,
    },
    {
        "source_idx": 2,
        "url": "http://darkmarket3fg8abc.onion/listing/7721",
        "title": "RDP Access — US corporate network, admin privileges",
        "text": (
            "Selling RDP access with domain admin privileges to mid-size US logistics company. "
            "Network has ~500 endpoints, no EDR detected. "
            "Ransomware-ready environment. Internal backups visible. "
            "Revenue ~$120M/year according to LinkedIn. "
            "Asking 1.5 BTC. Will accept offers."
        ),
        "keywords": ["RDP access", "admin", "ransomware"],
        "days_ago": 4,
    },
    {
        "source_idx": 3,
        "url": "http://leakbasexy5d62abc.onion/leaks/linkedin-scrape-2026",
        "title": "LinkedIn scrape — 180M records with emails",
        "text": (
            "Latest LinkedIn scrape with verified emails. "
            "180 million professional profiles with: full name, email, "
            "employer, job title, location, connections count. "
            "Useful for spear-phishing targeting. Includes acme-corp.com employees: "
            "found 847 profiles. Available in CSV/JSON. "
            "Free sample: 10K records on request."
        ),
        "keywords": ["acme-corp.com", "LinkedIn", "phishing", "email"],
        "days_ago": 20,
    },
    {
        "source_idx": 4,
        "url": "http://exploitin9xyz1234.onion/forum/post/95001",
        "title": "Ransomware affiliate program — 80/20 split",
        "text": (
            "Recruiting affiliates for our RaaS operation. "
            "We provide: builder, C2 infrastructure, victim negotiation, "
            "data leak site hosting. You provide: initial access. "
            "80%% split for affiliates on ransoms over $1M. "
            "Currently targeting healthcare, legal, and financial sectors. "
            "Proven track record: 40+ successful operations in 2025."
        ),
        "keywords": ["ransomware", "RaaS", "affiliate"],
        "days_ago": 7,
    },
    {
        "source_idx": 0,
        "url": "http://breachforumsukll3457.onion/thread/19441",
        "title": "SSN + DOB combo — US citizens, 45K records",
        "text": (
            "PII database for identity theft operations. "
            "45,000 US citizens with: full name, SSN, DOB, address, phone. "
            "Cross-referenced with credit bureau data. "
            "High-value targets — average credit score 720+. "
            "Perfect for opening credit lines, tax fraud, or synthetic identity. "
            "Price: $2 per record, bulk deals available."
        ),
        "keywords": ["SSN", "identity theft", "PII", "DOB"],
        "days_ago": 9,
    },
    {
        "source_idx": 2,
        "url": "http://darkmarket3fg8abc.onion/listing/9102",
        "title": "Custom phishing kit — branded acme-corp.com",
        "text": (
            "Selling custom phishing kit mimicking acme-corp.com login portal. "
            "Includes: pixel-perfect replica of their SSO login page, "
            "2FA bypass module, real-time credential forwarding to Telegram bot. "
            "Tested against their email gateway — bypasses current filters. "
            "Price: 0.1 BTC includes 30 days of hosting on bulletproof server."
        ),
        "keywords": ["acme-corp.com", "phishing kit", "2FA bypass"],
        "days_ago": 1,
    },
]

# ── Seed logic ─────────────────────────────────────────────────────────────────

async def seed():
    engine = create_async_engine(settings.database_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    es = get_es_client()

    print("Seeding demo data...")

    async with Session() as db:
        # ── Sources ──────────────────────────────────────────────────────────
        source_ids: list[int] = []
        for s in SOURCES:
            existing = await db.execute(
                select(Source).where(Source.onion_url == s["onion_url"])
            )
            src = existing.scalar_one_or_none()
            if not src:
                src = Source(
                    name=s["name"],
                    onion_url=s["onion_url"],
                    crawl_frequency_hours=24,
                    is_active=True,
                    last_crawled_at=now - timedelta(hours=randint(1, 5)),
                )
                db.add(src)
                await db.flush()
                print(f"  + Source: {src.name}")
            source_ids.append(src.id)
        await db.commit()

        # ── Findings ─────────────────────────────────────────────────────────
        finding_ids: list[int] = []
        for raw in FINDINGS:
            content_hash = hashlib.sha256(raw["text"].encode()).hexdigest()
            existing = await db.execute(
                select(Finding).where(Finding.content_hash == content_hash)
            )
            if existing.scalar_one_or_none():
                print(f"  ~ Skipping duplicate: {raw['title'][:50]}")
                continue

            first_seen = now - timedelta(days=raw["days_ago"], hours=randint(0, 12))
            src_id = source_ids[raw["source_idx"]]
            finding = Finding(
                source_id=src_id,
                url=raw["url"],
                title=raw["title"],
                content_snippet=raw["text"][:500],
                content_hash=content_hash,
                matched_keywords=raw["keywords"],
                first_seen=first_seen,
                last_seen=first_seen + timedelta(hours=randint(0, 6)),
            )
            db.add(finding)
            await db.flush()
            finding_ids.append(finding.id)
            print(f"  + Finding: {raw['title'][:55]}")

            # Index in Elasticsearch
            try:
                await index_finding(es, {
                    "url": raw["url"],
                    "title": raw["title"],
                    "text": raw["text"],
                    "matched_keywords": raw["keywords"],
                    "source_id": src_id,
                    "content_hash": content_hash,
                    "first_seen": first_seen.isoformat(),
                    "last_seen": finding.last_seen.isoformat(),
                })
            except Exception as exc:
                print(f"    ! ES index failed: {exc}")

        await db.commit()

        # ── Alerts (for any active watchlists with alert configs) ─────────────
        wl_result = await db.execute(select(Watchlist).where(Watchlist.is_active.is_(True)))
        watchlists = wl_result.scalars().all()

        for wl in watchlists:
            terms = [t.lower() for t in (wl.keywords + wl.domains + wl.emails)]
            cfg_result = await db.execute(
                select(AlertConfig).where(AlertConfig.watchlist_id == wl.id)
            )
            configs = cfg_result.scalars().all()
            if not configs:
                continue

            for raw in FINDINGS:
                text_lower = raw["text"].lower()
                hits = [t for t in terms if t in text_lower]
                if not hits:
                    continue
                content_hash = hashlib.sha256(raw["text"].encode()).hexdigest()
                finding_row = await db.execute(
                    select(Finding).where(Finding.content_hash == content_hash)
                )
                finding = finding_row.scalar_one_or_none()
                if not finding:
                    continue
                for config in configs:
                    alert = Alert(
                        watchlist_id=wl.id,
                        finding_id=finding.id,
                        channel=config.channel,
                        delivered=False,
                        acknowledged=False,
                        triggered_at=finding.first_seen,
                    )
                    db.add(alert)
                    print(f"  + Alert: watchlist='{wl.name}' finding='{raw['title'][:40]}'")

        await db.commit()

    await es.close()
    await engine.dispose()
    print("\nDone. Refresh the dashboard to see findings and stats.")


if __name__ == "__main__":
    asyncio.run(seed())
