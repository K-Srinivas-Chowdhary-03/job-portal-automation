import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.schemas.job import JobDetailRead


class AdminJobAction(BaseModel):
    remarks: Optional[str] = None


class AdminDashboardStats(BaseModel):
    total_published: int
    pending_jobs: int
    approved_jobs: int
    rejected_jobs: int
    expired_jobs: int
    total_sources: int
    active_sources: int
    total_scraping_runs: int
    scraping_success_rate: float


class ScrapingRunRead(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    jobs_found: int
    jobs_processed: int
    jobs_failed: int
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RawJobRecordRead(BaseModel):
    id: uuid.UUID
    scraping_run_id: uuid.UUID
    normalized_job_id: Optional[uuid.UUID] = None
    source_external_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    extracted_text: Optional[str] = None
    ai_response: Optional[Dict[str, Any]] = None
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminJobReviewDetail(BaseModel):
    job: JobDetailRead
    raw_record: Optional[RawJobRecordRead] = None
