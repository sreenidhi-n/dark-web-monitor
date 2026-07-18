from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.finding import Finding
from app.models.user import User
from app.routers.auth import get_current_user
from app.search.client import get_es_client, search_findings

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingOut(BaseModel):
    id: int
    source_id: int
    url: str
    title: Optional[str]
    content_snippet: str
    matched_keywords: list[str]
    severity: str
    first_seen: datetime
    last_seen: datetime

    model_config = {"from_attributes": True}


class FindingsPage(BaseModel):
    items: list[FindingOut]
    total: int
    page: int
    page_size: int


class SearchHit(BaseModel):
    id: str
    score: float
    url: Optional[str]
    title: Optional[str]
    source_id: Optional[int]
    matched_keywords: list[str]
    highlights: list[str]


async def _get_finding_or_404(finding_id: int, db: AsyncSession) -> Finding:
    result = await db.execute(select(Finding).where(Finding.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding


@router.get("/", response_model=FindingsPage)
async def list_findings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None, description="Filter by a matched keyword"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    since: Optional[datetime] = Query(None, description="Return findings first seen after this timestamp"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = _build_filters(source_id, keyword, severity, since)

    total_result = await db.execute(select(func.count()).select_from(Finding).where(*filters))
    total = total_result.scalar_one()

    stmt = (
        select(Finding)
        .where(*filters)
        .order_by(Finding.first_seen.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    findings = (await db.execute(stmt)).scalars().all()

    return FindingsPage(items=findings, total=total, page=page, page_size=page_size)


@router.get("/search", response_model=list[SearchHit])
async def search(
    q: str = Query(..., min_length=2),
    size: int = Query(20, ge=1, le=100),
    from_: int = Query(0, ge=0, alias="from"),
    _: User = Depends(get_current_user),
):
    es = get_es_client()
    try:
        raw = await search_findings(es, q, size=size, from_=from_)
    finally:
        await es.close()

    hits = raw.get("hits", {}).get("hits", [])
    return [_shape_hit(h) for h in hits]


@router.get("/{finding_id}", response_model=FindingOut)
async def get_finding(
    finding_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_finding_or_404(finding_id, db)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_filters(
    source_id: Optional[int],
    keyword: Optional[str],
    severity: Optional[str],
    since: Optional[datetime],
) -> list:
    filters = []
    if source_id is not None:
        filters.append(Finding.source_id == source_id)
    if keyword:
        # PostgreSQL JSON @> containment — checks if the array includes this string
        filters.append(Finding.matched_keywords.contains([keyword]))
    if severity:
        filters.append(Finding.severity == severity)
    if since:
        filters.append(Finding.first_seen >= since)
    return filters


def _shape_hit(hit: dict) -> SearchHit:
    src = hit.get("_source", {})
    highlight_fragments = hit.get("highlight", {}).get("content", [])
    return SearchHit(
        id=hit["_id"],
        score=hit.get("_score") or 0.0,
        url=src.get("url"),
        title=src.get("title"),
        source_id=src.get("source_id"),
        matched_keywords=src.get("matched_keywords", []),
        highlights=highlight_fragments,
    )
