from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryRead

router = APIRouter()


@router.get("", response_model=List[CategoryRead])
async def list_categories(
    job_type: Optional[str] = Query(None, description="Filter by job type (PRIVATE, GOVERNMENT, BOTH)"),
    db: AsyncSession = Depends(get_db),
):
    """List all categories with optional job_type filter."""
    query = select(Category).order_by(Category.name)
    if job_type:
        query = query.where(Category.job_type.in_([job_type.upper(), "BOTH"]))
    result = await db.execute(query)
    return result.scalars().all()
