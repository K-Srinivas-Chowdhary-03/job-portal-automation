from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, HttpUrl, field_validator


class PrivateJobExtraction(BaseModel):
    """Schema for Grok AI extraction of private sector vacancies."""
    job_title: str
    company_name: str
    job_type: str = "PRIVATE"
    employment_type: str = "FULL_TIME"
    location: Optional[List[str]] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    qualifications: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    application_url: str
    application_deadline: Optional[str] = None
    description: str


class GovernmentJobExtraction(BaseModel):
    """Schema for Grok AI extraction of government recruitment notifications."""
    job_title: str
    recruitment_organization: str
    job_type: str = "GOVERNMENT"
    notification_number: Optional[str] = None
    vacancies_count: Optional[int] = None
    location: Optional[List[str]] = None
    age_limit_min: Optional[int] = None
    age_limit_max: Optional[int] = None
    qualifications: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    application_start_date: Optional[str] = None
    application_end_date: Optional[str] = None
    examination_date: Optional[str] = None
    application_url: str
    official_notification_pdf: Optional[str] = None
    description: str
