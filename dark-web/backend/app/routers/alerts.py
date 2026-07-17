from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert, AlertChannel
from app.models.alert_config import AlertConfig
from app.models.user import Role, User
from app.models.watchlist import Watchlist
from app.routers.auth import get_current_user, require_role

router = APIRouter(prefix="/alerts", tags=["alerts"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AlertConfigCreate(BaseModel):
    watchlist_id: int
    channel: AlertChannel
    destination: str = Field(..., min_length=1, max_length=512)


class AlertConfigOut(BaseModel):
    id: int
    watchlist_id: int
    channel: AlertChannel
    destination: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryOut(BaseModel):
    id: int
    watchlist_id: int
    finding_id: int
    triggered_at: datetime
    channel: AlertChannel
    delivered: bool
    acknowledged: bool
    acknowledged_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_watchlist_or_404(watchlist_id: int, db: AsyncSession) -> Watchlist:
    result = await db.execute(select(Watchlist).where(Watchlist.id == watchlist_id))
    wl = result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return wl


def _owned_watchlist_ids_subquery(current_user: User):
    """Subquery returning watchlist IDs visible to this user."""
    stmt = select(Watchlist.id).where(Watchlist.is_active.is_(True))
    if current_user.role != Role.admin:
        stmt = stmt.where(Watchlist.owner_id == current_user.id)
    return stmt


# ── Alert config endpoints ────────────────────────────────────────────────────

@router.get("/config", response_model=list[AlertConfigOut])
async def list_alert_configs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned = _owned_watchlist_ids_subquery(current_user)
    result = await db.execute(
        select(AlertConfig)
        .where(AlertConfig.watchlist_id.in_(owned), AlertConfig.is_active.is_(True))
        .order_by(AlertConfig.created_at.desc())
    )
    return result.scalars().all()


@router.post("/config", response_model=AlertConfigOut, status_code=status.HTTP_201_CREATED)
async def create_alert_config(
    payload: AlertConfigCreate,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    wl = await _get_watchlist_or_404(payload.watchlist_id, db)
    if current_user.role != Role.admin and wl.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your watchlist")

    config = AlertConfig(
        watchlist_id=payload.watchlist_id,
        channel=payload.channel,
        destination=payload.destination,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_config(
    config_id: int,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertConfig).where(AlertConfig.id == config_id))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert config not found")

    wl = await _get_watchlist_or_404(config.watchlist_id, db)
    if current_user.role != Role.admin and wl.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your watchlist")

    config.is_active = False
    await db.commit()


# ── Alert history endpoints ───────────────────────────────────────────────────

@router.get("/history", response_model=list[AlertHistoryOut])
async def alert_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    watchlist_id: Optional[int] = Query(None),
    delivered: Optional[bool] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    owned = _owned_watchlist_ids_subquery(current_user)
    stmt = select(Alert).where(Alert.watchlist_id.in_(owned))

    if watchlist_id is not None:
        stmt = stmt.where(Alert.watchlist_id == watchlist_id)
    if delivered is not None:
        stmt = stmt.where(Alert.delivered.is_(delivered))
    if acknowledged is not None:
        stmt = stmt.where(Alert.acknowledged.is_(acknowledged))

    stmt = stmt.order_by(Alert.triggered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/history/{alert_id}/acknowledge", response_model=AlertHistoryOut)
async def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_role("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")

    wl = await _get_watchlist_or_404(alert.watchlist_id, db)
    if current_user.role != Role.admin and wl.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your alert")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
