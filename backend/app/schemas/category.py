import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    job_type: str = "BOTH"


class CategoryCreate(CategoryBase):
    slug: str


class CategoryRead(CategoryBase):
    id: uuid.UUID
    slug: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
