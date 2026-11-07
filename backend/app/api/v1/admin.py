
import uuid

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import require_admin
from app.models.user import User
from app.models.job import Job
from app.models.source import Source
from app.models.scraping import ScrapingRun, RawJobRecord
from app.models.audit import JobReviewHistory

from app.schemas.job import (
    JobRead,
    JobDetailRead,
    JobUpdate,
    PaginatedJobs,
)
from app.schemas.source import SourceRead, SourceCreate, SourceUpdate
from app.schemas.admin import (
    AdminJobAction,
    AdminDashboardStats,
    ScrapingRunRead,
    AdminJobReviewDetail,
    RawJobRecordRead,
)

from app.services.job_service import allowed_transition


router = APIRouter()


# -----------------------------------------------------------------------------
# Admin Dashboard
# -----------------------------------------------------------------------------


@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard_metrics(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate statistics for admin dashboard overview."""

    total_pub = await db.scalar(
        select(func.count(Job.id)).where(Job.status == "PUBLISHED")
    ) or 0

    pending = await db.scalar(
        select(func.count(Job.id)).where(
            Job.status.in_(["PENDING", "UNDER_REVIEW"])
        )
    ) or 0

    approved = await db.scalar(
        select(func.count(Job.id)).where(Job.status == "APPROVED")
    ) or 0

    rejected = await db.scalar(
        select(func.count(Job.id)).where(Job.status == "REJECTED")
    ) or 0

    expired = await db.scalar(
        select(func.count(Job.id)).where(Job.status == "EXPIRED")
    ) or 0

    total_sources = await db.scalar(
        select(func.count(Source.id))
    ) or 0

    active_sources = await db.scalar(
        select(func.count(Source.id)).where(Source.is_active == True)
    ) or 0

    total_runs = await db.scalar(
        select(func.count(ScrapingRun.id))
    ) or 0

    completed_runs = await db.scalar(
        select(func.count(ScrapingRun.id)).where(
            ScrapingRun.status == "COMPLETED"
        )
    ) or 0

    success_rate = (
        round((completed_runs / total_runs * 100), 2)
        if total_runs > 0
        else 100.0
    )

    return AdminDashboardStats(
        total_published=total_pub,
        pending_jobs=pending,
        approved_jobs=approved,
        rejected_jobs=rejected,
        expired_jobs=expired,
        total_sources=total_sources,
        active_sources=active_sources,
        total_scraping_runs=total_runs,
        scraping_success_rate=success_rate,
    )


# -----------------------------------------------------------------------------
# Job Review
# -----------------------------------------------------------------------------


@router.get("/jobs/pending", response_model=List[JobRead])
async def list_pending_jobs(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all jobs pending administrator review."""

    query = (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.category),
        )
        .where(Job.status.in_(["PENDING", "UNDER_REVIEW"]))
        .order_by(desc(Job.created_at))
    )

    result = await db.execute(query)

    return result.scalars().all()


@router.get("/jobs/{job_id}", response_model=AdminJobReviewDetail)
async def get_job_for_review(
    job_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full review details including raw scraped payload."""

    job_query = (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.category),
        )
        .where(Job.id == job_id)
    )

    job_res = await db.execute(job_query)
    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    raw_res = await db.execute(
        select(RawJobRecord)
        .where(RawJobRecord.normalized_job_id == job_id)
        .order_by(desc(RawJobRecord.created_at))
    )

    raw_record = raw_res.scalars().first()

    return AdminJobReviewDetail(
        job=JobDetailRead.model_validate(job),
        raw_record=(
            RawJobRecordRead.model_validate(raw_record)
            if raw_record
            else None
        ),
    )


@router.patch("/jobs/{job_id}", response_model=JobRead)
async def update_job_details(
    job_id: uuid.UUID,
    job_in: JobUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edit job details and log the action in audit history."""

    job_res = await db.execute(
        select(Job).where(Job.id == job_id)
    )

    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    update_data = job_in.model_dump(exclude_unset=True)

    for field, val in update_data.items():
        setattr(job, field, val)

    audit = JobReviewHistory(
        id=uuid.uuid4(),
        job_id=job.id,
        admin_id=admin.id,
        action="EDIT",
        remarks="Admin updated job fields.",
    )

    db.add(audit)

    await db.commit()
    await db.refresh(job)

    return job


# -----------------------------------------------------------------------------
# Approve Job
# -----------------------------------------------------------------------------


@router.post("/jobs/{job_id}/approve", response_model=JobRead)
async def approve_job(
    job_id: uuid.UUID,
    action_in: AdminJobAction = AdminJobAction(),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending job vacancy."""

    job_res = await db.execute(
        select(Job).where(Job.id == job_id)
    )

    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Validate status transition
    if not allowed_transition(job.status, "APPROVED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status transition",
        )

    job.status = "APPROVED"
    job.approved_at = datetime.now(timezone.utc)

    audit = JobReviewHistory(
        id=uuid.uuid4(),
        job_id=job.id,
        admin_id=admin.id,
        action="APPROVE",
        remarks=action_in.remarks or "Approved for publication.",
    )

    db.add(audit)

    await db.commit()
    await db.refresh(job)

    return job


# -----------------------------------------------------------------------------
# Publish Job
# -----------------------------------------------------------------------------


@router.post("/jobs/{job_id}/publish", response_model=JobRead)
async def publish_job(
    job_id: uuid.UUID,
    action_in: AdminJobAction = AdminJobAction(),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Publish an approved job to the public website."""

    job_res = await db.execute(
        select(Job).where(Job.id == job_id)
    )

    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Validate status transition
    if not allowed_transition(job.status, "PUBLISHED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status transition",
        )

    job.status = "PUBLISHED"
    job.published_at = datetime.now(timezone.utc)

    if not job.approved_at:
        job.approved_at = datetime.now(timezone.utc)

    audit = JobReviewHistory(
        id=uuid.uuid4(),
        job_id=job.id,
        admin_id=admin.id,
        action="PUBLISH",
        remarks=action_in.remarks or "Published to public website.",
    )

    db.add(audit)

    await db.commit()
    await db.refresh(job)

    return job


# -----------------------------------------------------------------------------
# Reject Job
# -----------------------------------------------------------------------------


@router.post("/jobs/{job_id}/reject", response_model=JobRead)
async def reject_job(
    job_id: uuid.UUID,
    action_in: AdminJobAction,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending job with audit remarks."""

    job_res = await db.execute(
        select(Job).where(Job.id == job_id)
    )

    job = job_res.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Validate status transition
    if not allowed_transition(job.status, "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status transition",
        )

    job.status = "REJECTED"

    audit = JobReviewHistory(
        id=uuid.uuid4(),
        job_id=job.id,
        admin_id=admin.id,
        action="REJECT",
        remarks=action_in.remarks or "Rejected by administrator.",
    )

    db.add(audit)

    await db.commit()
    await db.refresh(job)

    return job


# -----------------------------------------------------------------------------
# Source Management
# -----------------------------------------------------------------------------


@router.get("/sources", response_model=List[SourceRead])
async def list_sources(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all configured scraping sources."""

    result = await db.execute(
        select(Source).order_by(desc(Source.created_at))
    )

    return result.scalars().all()


@router.post(
    "/sources",
    response_model=SourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_source(
    source_in: SourceCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Register a new job source."""

    source = Source(
        id=uuid.uuid4(),
        name=source_in.name,
        source_url=source_in.source_url,
        source_type=source_in.source_type,
        scraper_type=source_in.scraper_type,
        schedule_minutes=source_in.schedule_minutes,
        config=source_in.config or {},
        is_active=source_in.is_active,
    )

    db.add(source)

    await db.commit()
    await db.refresh(source)

    return source


@router.patch("/sources/{source_id}", response_model=SourceRead)
async def update_source(
    source_id: uuid.UUID,
    source_in: SourceUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update source configuration, schedule, or active status."""

    res = await db.execute(
        select(Source).where(Source.id == source_id)
    )

    source = res.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    for field, val in source_in.model_dump(exclude_unset=True).items():
        setattr(source, field, val)

    await db.commit()
    await db.refresh(source)

    return source


# -----------------------------------------------------------------------------
# Scraping Management
# -----------------------------------------------------------------------------


@router.get("/scraping/runs", response_model=List[ScrapingRunRead])
async def list_scraping_runs(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """View past scraping run logs."""

    result = await db.execute(
        select(ScrapingRun)
        .order_by(desc(ScrapingRun.started_at))
        .limit(50)
    )

    return result.scalars().all()


@router.post("/scraping/run")
async def trigger_manual_scraping(
    source_id: uuid.UUID = Query(
        ...,
        description="Source UUID to scrape",
    ),
    admin: User = Depends(require_admin),
):
    """Trigger an immediate scraping execution for a source."""

    try:
        from app.tasks.scrape_tasks import scrape_source_task

        task = scrape_source_task.delay(str(source_id))

        return {
            "status": "queued",
            "task_id": str(task.id),
            "source_id": str(source_id),
        }

    except Exception:
        # Fallback to direct async execution if Redis is unavailable.
        from app.tasks.scrape_tasks import _execute_source_scrape

        result = await _execute_source_scrape(str(source_id))

        return {
            "status": "executed_direct",
            "result": result,
        }
