"""
Celery scraping tasks.

Architecture note:
  - All DB operations use the SYNCHRONOUS psycopg2 session (SyncSessionLocal)
    to avoid asyncpg / Windows ProactorEventLoop conflicts inside Celery workers.
  - Only the actual web-scraping coroutine (Playwright / httpx) runs inside a
    fresh asyncio event loop via _run_async().
"""
import asyncio
import uuid
import logging
from datetime import datetime, timezone
from urllib.parse import quote_plus

from sqlalchemy import select, and_

from app.tasks.celery_app import celery_app
from app.core.database import SyncSessionLocal
from app.models.source import Source
from app.models.job import Job
from app.models.scraping import ScrapingRun, RawJobRecord
from app.scrapers.registry import get_scraper_for_source
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Run an async coroutine in a brand-new, isolated event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        finally:
            loop.close()
            asyncio.set_event_loop(None)


def _get_sync_db_url() -> str:
    """Build a psycopg2 connection string from settings, URL-encoding the password."""
    password = quote_plus(settings.POSTGRES_PASSWORD)
    return (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{password}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


# ---------------------------------------------------------------------------
# Core scraping logic  (sync DB, async scraper)
# ---------------------------------------------------------------------------

def _execute_source_scrape_sync(source_id_str: str) -> dict:
    """
    Scrape one source using a SYNC DB session.
    Only the actual HTTP/browser scraping runs in an async loop.
    """
    source_uuid = uuid.UUID(source_id_str)

    with SyncSessionLocal() as session:
        # --- Load source ---
        source = session.execute(
            select(Source).where(Source.id == source_uuid)
        ).scalar_one_or_none()

        if not source or not source.is_active:
            return {"status": "skipped", "reason": "Source inactive or not found"}

        # --- Create scraping run record ---
        scraping_run = ScrapingRun(
            id=uuid.uuid4(),
            source_id=source.id,
            started_at=datetime.now(timezone.utc),
            status="RUNNING",
        )
        session.add(scraping_run)
        session.commit()
        session.refresh(scraping_run)

        source_url = source.source_url
        scraper_type = source.scraper_type
        config = source.config or {}
        source_id = source.id
        scraping_run_id = scraping_run.id

        try:
            # --- Run async scraper in isolated loop ---
            scraper = get_scraper_for_source(
                scraper_type=scraper_type,
                source_url=source_url,
                config=config,
            )
            raw_items = _run_async(scraper.collect_raw_jobs())

            jobs_found = len(raw_items)
            processed = 0
            failed = 0

            for item in raw_items:
                try:
                    _save_raw_job_sync(
                        session=session,
                        source_id=source_id,
                        scraping_run_id=scraping_run_id,
                        item=item,
                    )
                    processed += 1
                except Exception as item_err:
                    logger.error(f"Failed saving item from {source_url}: {item_err}")
                    failed += 1

            # --- Update scraping run ---
            run = session.get(ScrapingRun, scraping_run_id)
            if run:
                run.jobs_found = jobs_found
                run.jobs_processed = processed
                run.jobs_failed = failed
                run.status = "COMPLETED"
                run.completed_at = datetime.now(timezone.utc)

            src = session.get(Source, source_id)
            if src:
                src.last_scraped_at = datetime.now(timezone.utc)

            session.commit()

            return {
                "status": "completed",
                "jobs_found": jobs_found,
                "processed": processed,
                "failed": failed,
            }

        except Exception as exc:
            logger.error(f"Scraping failed for source {source_id_str}: {exc}")
            run = session.get(ScrapingRun, scraping_run_id)
            if run:
                run.status = "FAILED"
                run.error_message = str(exc)[:1000]
                run.completed_at = datetime.now(timezone.utc)
                session.commit()
            return {"status": "failed", "error": str(exc)[:500]}


def _save_raw_job_sync(session, source_id, scraping_run_id, item: dict):
    """Persist one raw scraped item as a RawJobRecord (sync) and enqueue job creation."""
    record = RawJobRecord(
        id=uuid.uuid4(),
        scraping_run_id=scraping_run_id,
        source_external_id=item.get("external_id"),
        raw_data=item,
        extracted_text=item.get("description", "")[:10000],
        processing_status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    session.add(record)
    session.flush()   # get the ID without full commit
    # Enqueue the next step – create a validated Job from this raw record
    from app.tasks.scrape_tasks import process_raw_job_task
    process_raw_job_task.delay(str(record.id))

# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.scrape_tasks.scrape_source_task",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def scrape_source_task(self, source_id: str):
    """Celery task: scrape one job source."""
    try:
        return _execute_source_scrape_sync(source_id)
    except Exception as exc:
        logger.error(f"scrape_source_task failed for {source_id}: {exc}")
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


def _queue_sources_by_type(source_type: str):
    """Enqueue scraping tasks for all active sources of the given type (sync)."""
    with SyncSessionLocal() as session:
        sources = session.execute(
            select(Source).where(
                and_(Source.is_active == True, Source.source_type == source_type)
            )
        ).scalars().all()
        logger.info(f"Queuing {len(sources)} {source_type} sources.")
        for src in sources:
            scrape_source_task.delay(str(src.id))


@celery_app.task(name="app.tasks.scrape_tasks.scheduled_scrape_private_sources")
def scheduled_scrape_private_sources():
    """Scheduled task: queue all active PRIVATE source scrapes."""
    _queue_sources_by_type("PRIVATE")


@celery_app.task(name="app.tasks.scrape_tasks.scheduled_scrape_govt_sources")
def scheduled_scrape_govt_sources():
    """Scheduled task: queue all active GOVERNMENT source scrapes."""
    _queue_sources_by_type("GOVERNMENT")


@celery_app.task(name="app.tasks.scrape_tasks.verify_job_expiry_task")
def verify_job_expiry_task():
    """Daily task: mark past-deadline PUBLISHED jobs as EXPIRED."""
    with SyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        expired = session.execute(
            select(Job).where(
                and_(
                    Job.status == "PUBLISHED",
                    Job.application_deadline < now,
                )
            )
        ).scalars().all()
        for j in expired:
            j.status = "EXPIRED"
        if expired:
            logger.info(f"Marked {len(expired)} jobs as EXPIRED.")
        session.commit()
