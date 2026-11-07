from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Source(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="PRIVATE", nullable=False)  # PRIVATE, GOVERNMENT
    scraper_type: Mapped[str] = mapped_column(String(50), default="HTML", nullable=False)  # API, RSS, HTML, PLAYWRIGHT, PDF
    schedule_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    scraping_runs = relationship("ScrapingRun", back_populates="source", cascade="all, delete-orphan")
    job_sources = relationship("JobSource", back_populates="source", cascade="all, delete-orphan")
