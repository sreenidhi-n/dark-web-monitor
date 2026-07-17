import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import alerts, auth, export, findings, sources, watchlists
from app.search.client import ensure_index, get_es_client

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Dark Web Monitor API")
    es = get_es_client()
    await ensure_index(es)
    await es.close()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Dark Web Monitor",
    description="Self-hosted dark web monitoring and alerting platform.",
    version="0.1.0",
    contact={"name": "DWM Project", "url": "https://github.com/your-handle/dark-web-monitor"},
    lifespan=lifespan,
)

# Restrict origins in production — update with your domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(watchlists.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "0.1.0"}
