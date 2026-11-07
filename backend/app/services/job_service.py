
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job
from app.models.company import Company
from app.models.source import Source
from app.models.job_source import JobSource
from app.models.scraping import ScrapingRun, RawJobRecord
from app.scrapers.base import ScrapedItem
from app.ai.client import grok_client
from app.services.duplicate_detector import (
    DuplicateDetector,
    canonicalize_url,
    generate_content_fingerprint,
)


def slugify(text: str) -> str:
    """Generate URL-safe slug from title with random suffix to ensure uniqueness."""
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', text.lower())
    clean = re.sub(r'[\s-]+', '-', clean).strip('-')
    random_suffix = uuid.uuid4().hex[:6]
    return f"{clean[:100]}-{random_suffix}"


def allowed_transition(current: str, target: str) -> bool:
    """
    Check whether a job status transition is allowed.

    Allowed transitions:
        PENDING  -> APPROVED
        PENDING  -> REJECTED
        APPROVED -> PUBLISHED
    """
    allowed = {
        "PENDING": {"APPROVED", "REJECTED"},
        "APPROVED": {"PUBLISHED"},
    }

    return target in allowed.get(current, set())


class JobIngestionService:
    """Orchestrates raw record archiving, Grok AI extraction, deduplication, and PENDING job creation."""

    @staticmethod
    async def process_scraped_item(
        db: AsyncSession,
        source: Source,
        scraping_run: ScrapingRun,
        item: ScrapedItem,
    ) -> Optional[Job]:
        # 1. Create and save RawJobRecord
        raw_record = RawJobRecord(
            id=uuid.uuid4(),
            scraping_run_id=scraping_run.id,
            source_external_id=item.external_id,
            raw_data={"url": item.source_url, "metadata": item.metadata},
            extracted_text=item.text_content,
            processing_status="PENDING",
        )
        db.add(raw_record)
        await db.flush()

        try:
            # 2. Extract structured data via Grok AI
            ai_data = await grok_client.extract_job_data(
                raw_text=item.text_content,
                source_type=source.source_type,
                fallback_url=item.source_url,
            )
            raw_record.ai_response = ai_data

            title = ai_data.get("job_title") or item.title
            company_name = (
                ai_data.get("company_name")
                or ai_data.get("recruitment_organization")
                or source.name
            )
            raw_loc = ai_data.get("location")
            location_str = (
                ", ".join(raw_loc)
                if isinstance(raw_loc, list)
                else (raw_loc or "Multiple Locations")
            )
            app_url = canonicalize_url(
                ai_data.get("application_url") or item.source_url
            )
            fingerprint = generate_content_fingerprint(
                title, company_name, location_str
            )

            # 3. Duplicate Detection
            is_dup, existing_job = await DuplicateDetector.find_existing_job(
                db=db,
                source_id=source.id,
                external_id=item.external_id,
                application_url=app_url,
                fingerprint=fingerprint,
            )

            if is_dup and existing_job:
                raw_record.processing_status = "DUPLICATE"
                raw_record.normalized_job_id = existing_job.id

                js_res = await db.execute(
                    select(JobSource).where(
                        JobSource.job_id == existing_job.id,
                        JobSource.source_id == source.id,
                    )
                )
                existing_js = js_res.scalar_one_or_none()

                if existing_js:
                    existing_js.last_seen_at = datetime.now(timezone.utc)

                await db.commit()
                return existing_job

            # 4. Resolve or create Company
            company_res = await db.execute(
                select(Company).where(Company.name == company_name)
            )
            company = company_res.scalar_one_or_none()

            if not company:
                company = Company(
                    id=uuid.uuid4(),
                    name=company_name,
                    slug=slugify(company_name),
                    website=source.source_url,
                )
                db.add(company)
                await db.flush()

            # 5. Parse application deadline
            deadline_dt = None

            if ai_data.get("application_deadline"):
                try:
                    deadline_dt = datetime.fromisoformat(
                        ai_data["application_deadline"]
                    ).replace(tzinfo=timezone.utc)
                except Exception:
                    deadline_dt = None

            # 6. Create normalized Job
            # Every scraped job must start as PENDING.
            new_job = Job(
                id=uuid.uuid4(),
                company_id=company.id,
                category_id=None,
                title=title,
                slug=slugify(title),
                description=ai_data.get("description") or item.text_content,
                job_type=source.source_type,
                employment_type=ai_data.get(
                    "employment_type", "FULL_TIME"
                ),
                location=location_str,
                experience_min=ai_data.get("experience_min"),
                experience_max=ai_data.get("experience_max"),
                qualification=ai_data.get("qualifications", []),
                salary_min=ai_data.get("salary_min"),
                salary_max=ai_data.get("salary_max"),
                skills=ai_data.get("skills", []),
                application_url=app_url,
                application_deadline=deadline_dt,
                status="PENDING",
            )

            db.add(new_job)
            await db.flush()

            # 7. Map JobSource
            job_source = JobSource(
                id=uuid.uuid4(),
                job_id=new_job.id,
                source_id=source.id,
                external_job_id=item.external_id,
                source_job_url=item.source_url,
                content_fingerprint=fingerprint,
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
            db.add(job_source)

            # 8. Mark raw record as processed
            raw_record.normalized_job_id = new_job.id
            raw_record.processing_status = "PROCESSED"

            await db.commit()
            return new_job

        except Exception as exc:
            raw_record.processing_status = "FAILED"
            raw_record.error_message = str(exc)
            await db.commit()
            raise
