# -*- coding: utf-8 -*-
"""Job creation pipeline used by Celery after a raw scrape.

The pipeline:
1. Load the RawJobRecord (sync DB session).
2. Call GrokAIClient.extract_job_data (async) via a temporary event loop.
3. Validate the result with the appropriate Pydantic schema.
4. Generate a content fingerprint.
5. Run duplicate detection (sync wrapper).
6. If not duplicate, create / fetch Company, Category, Job and JobSource rows.
7. Mark the RawJobRecord processing_status = "COMPLETED" (or "FAILED").
"""

import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.database import SyncSessionLocal
from app.models.raw_job_record import RawJobRecord  # noqa: F401 – placeholder for import path
from app.models.job import Job
from app.models.company import Company
from app.models.category import Category
from app.models.job_source import JobSource
from app.models.source import Source
from app.ai.client import grok_client
from app.schemas.ai_extraction import PrivateJobExtraction, GovernmentJobExtraction
from app.services.duplicate_detector import (
    generate_content_fingerprint,
    DuplicateDetector,
    # sync wrapper will be added later
)

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Execute an async coroutine in a fresh event loop (sync context)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def _extract_job(raw_text: str, source_type: str, fallback_url: str) -> Dict[str, Any]:
    """Call Grok AI (or fallback) and return a dict of extracted fields.
    Exceptions are caught upstream – we always return a dict.
    """
    return _run_async(grok_client.extract_job_data(raw_text, source_type, fallback_url))


def _validate_extraction(data: Dict[str, Any], source_type: str) -> Optional[Dict[str, Any]]:
    """Validate the extraction dict with the correct Pydantic model.
    Returns the validated dict (model_dump) or ``None`` on validation error.
    """
    try:
        if source_type.upper() == "GOVERNMENT":
            model = GovernmentJobExtraction.model_validate(data)
        else:
            model = PrivateJobExtraction.model_validate(data)
        return model.model_dump()
    except Exception as exc:  # pragma: no cover – exercised in tests
        logger.error(f"AI extraction validation failed: {exc}")
        return None


def _get_or_create_company(session, name: str) -> Company:
    company = session.query(Company).filter(Company.name == name).first()
    if company:
        return company
    slug = name.lower().replace(" ", "-")
    company = Company(id=uuid.uuid4(), name=name, slug=slug)
    session.add(company)
    session.flush()
    return company


def _get_or_create_category(session, name: str) -> Category:
    cat = session.query(Category).filter(Category.name == name).first()
    if cat:
        return cat
    slug = name.lower().replace(" ", "-")
    cat = Category(id=uuid.uuid4(), name=name, slug=slug)
    session.add(cat)
    session.flush()
    return cat


def process_raw_job(raw_job_id: str) -> Dict[str, Any]:
    """Entry point called by a Celery task.

    Returns a dict with ``status`` ("created", "duplicate", "failed") and optional ``job_id``.
    """
    with SyncSessionLocal() as session:
        raw = session.query(RawJobRecord).filter(RawJobRecord.id == uuid.UUID(raw_job_id)).first()
        if not raw:
            logger.error(f"RawJobRecord {raw_job_id} not found")
            return {"status": "failed", "reason": "raw_not_found"}

        source = session.query(Source).filter(Source.id == raw.scraping_run.source_id).first()
        if not source:
            logger.error(f"Source for RawJobRecord {raw_job_id} not found")
            raw.processing_status = "FAILED"
            session.commit()
            return {"status": "failed", "reason": "source_not_found"}

        raw_text = raw.raw_data.get("description", "") or raw.raw_data.get("content", "")
        fallback_url = raw.raw_data.get("application_url", source.source_url)
        extracted = _extract_job(raw_text, source.source_type, fallback_url)
        validated = _validate_extraction(extracted, source.source_type)
        if not validated:
            raw.processing_status = "FAILED"
            session.commit()
            return {"status": "failed", "reason": "validation_error"}

        # Determine fields common to both schemas
        job_title = validated.get("job_title")
        company_name = validated.get("company_name") or validated.get("recruitment_organization")
        application_url = validated.get("application_url")
        category_name = validated.get("job_type", "General")
        location = (validated.get("location") or [None])[0]
        fingerprint = generate_content_fingerprint(job_title, company_name or "", location)

        # Duplicate detection – we need a sync wrapper around the async method
        is_dup, existing_job = DuplicateDetector.find_existing_job_sync(
            source_id=source.id,
            external_id=raw.raw_data.get("external_id"),
            application_url=application_url,
            fingerprint=fingerprint,
        )
        if is_dup:
            raw.processing_status = "SKIPPED_DUPLICATE"
            session.commit()
            return {"status": "duplicate", "existing_job_id": str(existing_job.id) if existing_job else None}

        # Create related entities
        company = _get_or_create_company(session, company_name or "Unknown")
        category = _get_or_create_category(session, category_name)

        job = Job(
            id=uuid.uuid4(),
            company_id=company.id,
            category_id=category.id,
            title=job_title,
            slug=job_title.lower().replace(" ", "-")[0:200],
            description=validated.get("description", ""),
            job_type=validated.get("job_type", "PRIVATE"),
            employment_type=validated.get("employment_type", "FULL_TIME"),
            location=location or "",
            experience_min=validated.get("experience_min"),
            experience_max=validated.get("experience_max"),
            qualification=validated.get("qualifications"),
            salary_min=validated.get("salary_min"),
            salary_max=validated.get("salary_max"),
            skills=validated.get("skills"),
            application_url=application_url,
            application_deadline=validated.get("application_deadline"),
            source_published_at=datetime.now(timezone.utc),
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(job)
        session.flush()

        # Link source ↔ job
        job_source = JobSource(
            id=uuid.uuid4(),
            job_id=job.id,
            source_id=source.id,
            external_job_id=raw.raw_data.get("external_id"),
            source_job_url=application_url,
            content_fingerprint=fingerprint,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        session.add(job_source)

        # Update raw record status
        raw.processing_status = "COMPLETED"
        raw.normalized_job_id = job.id
        session.commit()
        return {"status": "created", "job_id": str(job.id)}

# NOTE: The sync wrapper for DuplicateDetector is added in the same module for clarity.

# ---------------------------------------------------------------------------
# Sync wrapper around the async duplicate detector
# ---------------------------------------------------------------------------

def _run_async_sync(coro):
    """Helper used by the sync wrapper – identical to _run_async above but kept for naming clarity."""
    return _run_async(coro)


def _duplicate_detector_sync(
    source_id: uuid.UUID,
    external_id: Optional[str],
    application_url: str,
    fingerprint: str,
) -> tuple[bool, Optional[Job]]:
    """Run the async ``DuplicateDetector.find_existing_job`` inside a sync context.
    Returns ``(is_duplicate, existing_job)`` where ``existing_job`` may be ``None``.
    """
    async def _inner():
        async with AsyncSessionLocal() as async_db:  # type: ignore  # imported lazily below
            return await DuplicateDetector.find_existing_job(
                db=async_db,
                source_id=source_id,
                external_id=external_id,
                application_url=application_url,
                fingerprint=fingerprint,
            )

    # Import AsyncSessionLocal lazily to avoid circular imports at module load time
    from app.core.database import AsyncSessionLocal

    return _run_async_sync(_inner())


# Attach the sync helper to the class for easy import elsewhere
DuplicateDetector.find_existing_job_sync = staticmethod(_duplicate_detector_sync)
