import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class SourceBase(BaseModel):
    name: str
    source_url: str
    source_type: str = "PRIVATE"  # PRIVATE, GOVERNMENT
    scraper_type: str = "HTML"    # API, RSS, HTML, PLAYWRIGHT, PDF
    schedule_minutes: int = 60
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    scraper_type: Optional[str] = None
    schedule_minutes: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SourceRead(SourceBase):
    id: uuid.UUID
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
