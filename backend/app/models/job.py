import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(350), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), default="PRIVATE", nullable=False, index=True)  # PRIVATE, GOVERNMENT
    employment_type: Mapped[str] = mapped_column(String(50), default="FULL_TIME", nullable=False)  # FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    experience_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    qualification: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=True
    )
    
    salary_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    
    skills: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=True
    )
    
    application_url: Mapped[str] = mapped_column(String(1500), nullable=False, index=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status: PENDING, UNDER_REVIEW, APPROVED, REJECTED, PUBLISHED, EXPIRED, CLOSED
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="jobs")
    category = relationship("Category", back_populates="jobs")
    job_sources = relationship("JobSource", back_populates="job", cascade="all, delete-orphan")
    job_skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    saved_by_users = relationship("SavedJob", back_populates="job", cascade="all, delete-orphan")
    reviews = relationship("JobReviewHistory", back_populates="job", cascade="all, delete-orphan")
    raw_records = relationship("RawJobRecord", back_populates="normalized_job")


# Composite indexes for high-frequency queries
Index("idx_jobs_status_published", Job.status, Job.published_at)
Index("idx_jobs_type_status", Job.job_type, Job.status)
Index("idx_jobs_location_status", Job.location, Job.status)
