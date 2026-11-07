import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.company import CompanyRead
from app.schemas.category import CategoryRead


class JobBase(BaseModel):
    title: str
    description: str
    job_type: str = "PRIVATE"  # PRIVATE, GOVERNMENT
    employment_type: str = "FULL_TIME"
    location: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    qualification: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    skills: Optional[List[str]] = None
    application_url: str
    application_deadline: Optional[datetime] = None


class JobCreate(JobBase):
    company_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    slug: Optional[str] = None
    source_published_at: Optional[datetime] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    job_type: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    qualification: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    skills: Optional[List[str]] = None
    application_url: Optional[str] = None
    application_deadline: Optional[datetime] = None
    status: Optional[str] = None


class JobRead(BaseModel):
    id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    title: str
    slug: str
    job_type: str
    employment_type: str
    location: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    qualification: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    skills: Optional[List[str]] = None
    application_url: str
    application_deadline: Optional[datetime] = None
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime

    company: Optional[CompanyRead] = None
    category: Optional[CategoryRead] = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailRead(JobRead):
    description: str
    source_published_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None


class PaginatedJobs(BaseModel):
    items: List[JobRead]
    total: int
    page: int
    size: int
    pages: int
