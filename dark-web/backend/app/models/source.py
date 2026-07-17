from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    onion_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    crawl_frequency_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="source")  # noqa: F821
