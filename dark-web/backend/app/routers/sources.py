from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.scheduler import crawl_source
from app.database import get_db
from app.models.source import Source
from app.models.user import User
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    onion_url: str
    crawl_frequency_hours: int = Field(24, ge=1, le=8760)

    @field_validator("onion_url")
    @classmethod
    def validate_onion_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        # Allow bare hostname without scheme — normalise to http://
        parsed = urlparse(v if "://" in v else f"http://{v}")
        if parsed.scheme not in ("http", "https"):
            raise ValueError("onion_url must start with http:// or https://")
        if not parsed.netloc.endswith(".onion"):
            raise ValueError("onion_url must be a .onion address")
        return v


class SourceOut(BaseModel):
    id: int
    name: str
    onion_url: str
    crawl_frequency_hours: int
    last_crawled_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    created_by_id: Optional[int]

    model_config = {"from_attributes": True}


async def _get_source_or_404(source_id: int, db: AsyncSession) -> Source:
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.get("/", response_model=list[SourceOut])
async def list_sources(
    active_only: bool = Query(True, description="When true, returns only active sources"),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Source)
    if active_only:
        stmt = stmt.where(Source.is_active.is_(True))
    stmt = stmt.order_by(Source.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreate,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    source = Source(
        name=payload.name,
        onion_url=payload.onion_url,
        crawl_frequency_hours=payload.crawl_frequency_hours,
        created_by_id=current_user.id,
    )
    db.add(source)
    try:
        await db.commit()
        await db.refresh(source)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with this .onion URL already exists",
        )
    return source


@router.get("/{source_id}", response_model=SourceOut)
async def get_source(
    source_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_source_or_404(source_id, db)


@router.put("/{source_id}", response_model=SourceOut)
async def update_source(
    source_id: int,
    payload: SourceCreate,
    _: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    source = await _get_source_or_404(source_id, db)
    source.name = payload.name
    source.onion_url = payload.onion_url
    source.crawl_frequency_hours = payload.crawl_frequency_hours
    try:
        await db.commit()
        await db.refresh(source)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A source with this .onion URL already exists",
        )
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    source = await _get_source_or_404(source_id, db)
    source.is_active = False
    await db.commit()


@router.post("/{source_id}/crawl", status_code=status.HTTP_202_ACCEPTED)
async def trigger_crawl(
    source_id: int,
    _: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    source = await _get_source_or_404(source_id, db)
    if not source.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot crawl an inactive source — reactivate it first",
        )
    crawl_source.delay(source_id)
    return {"detail": f"Crawl enqueued for source {source_id}"}
