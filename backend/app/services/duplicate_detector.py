import hashlib
import re
import uuid
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.models.job import Job
from app.models.job_source import JobSource


def canonicalize_url(url: str) -> str:
    """Strip tracking parameters (utm_*, ref, etc.) and trailing slashes to obtain canonical URL."""
    try:
        parsed = urlparse(url.strip())
        # Remove query parameters commonly used for tracking
        cleaned_netloc = parsed.netloc.lower()
        cleaned_path = parsed.path.rstrip('/')
        return urlunparse((parsed.scheme.lower(), cleaned_netloc, cleaned_path, '', '', ''))
    except Exception:
        return url.strip().rstrip('/')


def generate_content_fingerprint(title: str, company_or_org: str, location: Optional[str]) -> str:
    """Compute deterministic SHA-256 fingerprint from normalized title, company, and location."""
    clean_title = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    clean_company = re.sub(r'[^a-zA-Z0-9]', '', (company_or_org or '').lower())
    clean_location = re.sub(r'[^a-zA-Z0-9]', '', (location or '').lower())
    
    payload = f"{clean_title}:{clean_company}:{clean_location}".encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


class DuplicateDetector:
    """Service to identify duplicate job notifications across sources."""

    @staticmethod
    async def find_existing_job(
        db: AsyncSession,
        source_id: uuid.UUID,
        external_id: Optional[str],
        application_url: str,
        fingerprint: str,
    ) -> Tuple[bool, Optional[Job]]:
        """
        Check whether this job already exists in the database.
        Returns (is_duplicate: bool, existing_job: Optional[Job])
        """
        canonical_url = canonicalize_url(application_url)

        # Check 1: External ID match on the same source
        if external_id:
            query = (
                select(Job)
                .join(JobSource, JobSource.job_id == Job.id)
                .where(
                    and_(
                        JobSource.source_id == source_id,
                        JobSource.external_job_id == external_id,
                    )
                )
            )
            res = await db.execute(query)
            existing = res.scalar_one_or_none()
            if existing:
                return True, existing

        # Check 2: Exact Canonical Application URL match
        url_query = select(Job).where(Job.application_url == canonical_url)
        res = await db.execute(url_query)
        existing = res.scalar_one_or_none()
        if existing:
            return True, existing

        # Check 3: Content Fingerprint match in job_sources
        fp_query = (
            select(Job)
            .join(JobSource, JobSource.job_id == Job.id)
            .where(JobSource.content_fingerprint == fingerprint)
        )
        res = await db.execute(fp_query)
        existing = res.scalar_one_or_none()
        if existing:
            return True, existing

        return False, None
