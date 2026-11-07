import math
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.job import Job
from app.models.company import Company
from app.models.category import Category
from app.schemas.job import JobRead, JobDetailRead, PaginatedJobs

router = APIRouter()


@router.get("", response_model=PaginatedJobs)
async def list_published_jobs(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    job_type: Optional[str] = Query(None, description="PRIVATE or GOVERNMENT"),
    category_id: Optional[str] = Query(None, description="Category UUID"),
    location: Optional[str] = Query(None, description="Location search"),
    experience_max: Optional[int] = Query(None, description="Max years of experience required"),
    db: AsyncSession = Depends(get_db),
):
    """List all publicly visible PUBLISHED jobs with optional filters and pagination."""
    query = (
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.category))
        .where(Job.status == "PUBLISHED")
    )
    count_query = select(func.count(Job.id)).where(Job.status == "PUBLISHED")

    if job_type:
        query = query.where(Job.job_type == job_type.upper())
        count_query = count_query.where(Job.job_type == job_type.upper())

    if category_id:
        query = query.where(Job.category_id == category_id)
        count_query = count_query.where(Job.category_id == category_id)

    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
        count_query = count_query.where(Job.location.ilike(f"%{location}%"))

    if experience_max is not None:
        query = query.where(
            or_(Job.experience_min <= experience_max, Job.experience_min.is_(None))
        )
        count_query = count_query.where(
            or_(Job.experience_min <= experience_max, Job.experience_min.is_(None))
        )

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginated items
    offset = (page - 1) * size
    query = query.order_by(desc(Job.published_at), desc(Job.created_at)).offset(offset).limit(size)
    items_result = await db.execute(query)
    items = items_result.scalars().all()

    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedJobs(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/private", response_model=PaginatedJobs)
async def list_private_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all published private sector jobs."""
    return await list_published_jobs(page=page, size=size, job_type="PRIVATE", db=db)


@router.get("/government", response_model=PaginatedJobs)
async def list_government_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all published government job notifications."""
    return await list_published_jobs(page=page, size=size, job_type="GOVERNMENT", db=db)


@router.get("/search", response_model=PaginatedJobs)
async def search_jobs(
    q: str = Query(..., min_length=1, description="Search keyword"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search published jobs by keyword matching title, description, skills, or location."""
    search_term = f"%{q}%"
    query = (
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.category))
        .where(
            Job.status == "PUBLISHED",
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
                Job.location.ilike(search_term),
            ),
        )
    )
    count_query = select(func.count(Job.id)).where(
        Job.status == "PUBLISHED",
        or_(
            Job.title.ilike(search_term),
            Job.description.ilike(search_term),
            Job.location.ilike(search_term),
        ),
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * size
    query = query.order_by(desc(Job.published_at)).offset(offset).limit(size)
    items_result = await db.execute(query)
    items = items_result.scalars().all()

    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedJobs(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{slug}", response_model=JobDetailRead)
async def get_job_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """Fetch complete details of a published job by slug."""
    query = (
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.category))
        .where(Job.slug == slug, Job.status == "PUBLISHED")
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job vacancy not found or not published.",
        )
    return job
