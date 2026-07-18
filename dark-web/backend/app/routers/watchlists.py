from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import Role, User
from app.models.watchlist import Watchlist, ThreatCategory
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    keywords: list[str] = []
    domains: list[str] = []
    emails: list[str] = []
    category: ThreatCategory = ThreatCategory.GENERAL

    @field_validator("keywords", "domains", "emails", mode="before")
    @classmethod
    def strip_and_deduplicate(cls, v: list) -> list:
        seen, result = set(), []
        for item in v:
            item = str(item).strip().lower()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result


class WatchlistOut(BaseModel):
    id: int
    name: str
    owner_id: int
    keywords: list[str]
    domains: list[str]
    emails: list[str]
    category: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


async def _get_watchlist_or_404(watchlist_id: int, db: AsyncSession) -> Watchlist:
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    wl = result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return wl


def _assert_owner_or_admin(watchlist: Watchlist, current_user: User) -> None:
    if current_user.role != Role.admin and watchlist.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your watchlist")


@router.get("/", response_model=list[WatchlistOut])
async def list_watchlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Watchlist).where(Watchlist.is_active.is_(True))
    # Admins see all watchlists; analysts and readonly users see only their own
    if current_user.role != Role.admin:
        stmt = stmt.where(Watchlist.owner_id == current_user.id)
    stmt = stmt.order_by(Watchlist.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=WatchlistOut, status_code=status.HTTP_201_CREATED)
async def create_watchlist(
    payload: WatchlistCreate,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    wl = Watchlist(
        name=payload.name,
        owner_id=current_user.id,
        keywords=payload.keywords,
        domains=payload.domains,
        emails=payload.emails,
        category=payload.category.value,
    )
    db.add(wl)
    await db.commit()
    await db.refresh(wl)
    return wl


@router.get("/{watchlist_id}", response_model=WatchlistOut)
async def get_watchlist(
    watchlist_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _assert_owner_or_admin(wl, current_user)
    return wl


@router.put("/{watchlist_id}", response_model=WatchlistOut)
async def update_watchlist(
    watchlist_id: int,
    payload: WatchlistCreate,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _assert_owner_or_admin(wl, current_user)
    wl.name = payload.name
    wl.keywords = payload.keywords
    wl.domains = payload.domains
    wl.emails = payload.emails
    wl.category = payload.category.value
    await db.commit()
    await db.refresh(wl)
    return wl


@router.delete("/{watchlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
    watchlist_id: int,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    wl = await _get_watchlist_or_404(watchlist_id, db)
    _assert_owner_or_admin(wl, current_user)
    wl.is_active = False
    await db.commit()
