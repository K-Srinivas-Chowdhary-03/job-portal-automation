import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.user_activity import SavedJob
from app.schemas.job import JobRead
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/saved-jobs", response_model=List[JobRead])
async def list_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all jobs saved/bookmarked by the authenticated user."""
    query = (
        select(Job)
        .join(SavedJob, SavedJob.job_id == Job.id)
        .options(selectinload(Job.company), selectinload(Job.category))
        .where(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/saved-jobs/{job_id}", status_code=status.HTTP_201_CREATED)
async def save_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save/bookmark a job for the current user."""
    # Verify job exists
    job_res = await db.execute(select(Job).where(Job.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Check if already saved
    existing_res = await db.execute(
        select(SavedJob).where(
            and_(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
        )
    )
    if existing_res.scalar_one_or_none():
        return {"message": "Job already saved"}

    saved = SavedJob(
        id=uuid.uuid4(),
        user_id=current_user.id,
        job_id=job_id,
    )
    db.add(saved)
    await db.commit()
    return {"message": "Job successfully saved"}


@router.delete("/saved-jobs/{job_id}")
async def unsave_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a job from user's bookmarks."""
    result = await db.execute(
        select(SavedJob).where(
            and_(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")

    await db.delete(saved)
    await db.commit()
    return {"message": "Job removed from saved list"}
