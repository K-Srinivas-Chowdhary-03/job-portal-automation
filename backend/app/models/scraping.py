import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin


class ScrapingRun(Base, UUIDMixin):
    __tablename__ = "scraping_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False, index=True)  # RUNNING, COMPLETED, FAILED
    
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    source = relationship("Source", back_populates="scraping_runs")
    raw_records = relationship("RawJobRecord", back_populates="scraping_run", cascade="all, delete-orphan")


class RawJobRecord(Base, UUIDMixin):
    __tablename__ = "raw_job_records"

    scraping_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scraping_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    raw_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    
    # Status: PENDING, PROCESSED, FAILED, DUPLICATE
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    scraping_run = relationship("ScrapingRun", back_populates="raw_records")
    normalized_job = relationship("Job", back_populates="raw_records")


Index("idx_raw_job_records_status", RawJobRecord.processing_status)
Index("idx_scraping_runs_status", ScrapingRun.status, ScrapingRun.started_at)
