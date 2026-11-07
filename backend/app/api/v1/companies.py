from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.company import Company
from app.schemas.company import CompanyRead

router = APIRouter()


@router.get("", response_model=List[CompanyRead])
async def list_companies(db: AsyncSession = Depends(get_db)):
    """List all registered companies."""
    result = await db.execute(select(Company).order_by(Company.name))
    return result.scalars().all()


@router.get("/{slug}", response_model=CompanyRead)
async def get_company_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    """Get company details by slug."""
    result = await db.execute(select(Company).where(Company.slug == slug))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
