import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin


class JobSource(Base, UUIDMixin):
    __tablename__ = "job_sources"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    source_job_url: Mapped[str] = mapped_column(String(1500), nullable=False)
    content_fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    job = relationship("Job", back_populates="job_sources")
    source = relationship("Source", back_populates="job_sources")


Index("idx_job_sources_fingerprint", JobSource.content_fingerprint)
Index("idx_job_sources_external_id", JobSource.source_id, JobSource.external_job_id)
