import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertChannel(str, enum.Enum):
    email = "email"
    slack = "slack"
    webhook = "webhook"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"), nullable=False, index=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    channel: Mapped[AlertChannel] = mapped_column(Enum(AlertChannel), nullable=False)
    delivered: Mapped[bool] = mapped_column(default=False, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(default=False, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    watchlist: Mapped["Watchlist"] = relationship("Watchlist")  # noqa: F821
    finding: Mapped["Finding"] = relationship("Finding")  # noqa: F821
