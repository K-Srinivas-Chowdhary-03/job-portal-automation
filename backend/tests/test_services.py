import pytest
from app.services.duplicate_detector import canonicalize_url, generate_content_fingerprint
from app.schemas.ai_extraction import PrivateJobExtraction, GovernmentJobExtraction
from app.scrapers.base import ScrapedItem
from app.ai.client import GrokAIClient


def test_url_canonicalization():
    """Verify tracking parameters and trailing slashes are cleanly removed."""
    url1 = "https://careers.google.com/jobs/results/12345/?utm_source=linkedin&utm_medium=cpc#apply"
    url2 = "https://careers.google.com/jobs/results/12345/"
    url3 = "https://careers.google.com/jobs/results/12345"

    c1 = canonicalize_url(url1)
    c2 = canonicalize_url(url2)
    c3 = canonicalize_url(url3)

    assert c1 == "https://careers.google.com/jobs/results/12345"
    assert c2 == "https://careers.google.com/jobs/results/12345"
    assert c3 == "https://careers.google.com/jobs/results/12345"


def test_content_fingerprint_generation():
    """Verify identical title, company, and location generate identical deterministic hashes."""
    fp1 = generate_content_fingerprint("Senior Python Engineer", "Google LLC", "Bangalore, India")
    fp2 = generate_content_fingerprint("senior python engineer ", "google llc", "Bangalore, India")
    fp3 = generate_content_fingerprint("Frontend Developer", "Google LLC", "Bangalore, India")

    assert fp1 == fp2
    assert fp1 != fp3


def test_private_job_pydantic_schema_validation():
    """Verify validation of private sector job data extracted via Grok AI."""
    sample_data = {
        "job_title": "Full Stack Developer",
        "company_name": "Acme Software Corp",
        "job_type": "PRIVATE",
        "location": ["Remote", "Hyderabad"],
        "experience_min": 2,
        "experience_max": 5,
        "qualifications": ["B.Tech Computer Science", "MCA"],
        "skills": ["Python", "FastAPI", "React", "Docker"],
        "salary_min": 1200000.0,
        "salary_max": 1800000.0,
        "application_url": "https://acme.com/careers/fullstack-456",
        "application_deadline": "2026-12-31",
        "description": "Develop high-scale cloud backend microservices and modern frontend applications.",
    }

    validated = PrivateJobExtraction.model_validate(sample_data)
    assert validated.job_title == "Full Stack Developer"
    assert validated.salary_min == 1200000.0
    assert len(validated.skills) == 4


def test_government_job_pydantic_schema_validation():
    """Verify validation of government recruitment notification extracted via Grok AI."""
    sample_govt = {
        "job_title": "Probationary Officer (PO)",
        "recruitment_organization": "State Bank of India (SBI)",
        "job_type": "GOVERNMENT",
        "notification_number": "CRPD/PO/2026-27/01",
        "vacancies_count": 2000,
        "location": ["All India"],
        "age_limit_min": 21,
        "age_limit_max": 30,
        "qualifications": ["Graduation in any discipline"],
        "skills": ["Quantitative Aptitude", "Reasoning", "English"],
        "salary_min": 65000.0,
        "salary_max": 80000.0,
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-04-30",
        "examination_date": "2026-06-15",
        "application_url": "https://sbi.co.in/careers",
        "official_notification_pdf": "https://sbi.co.in/docs/po_notification.pdf",
        "description": "Official recruitment for Probationary Officers across SBI branches nationwide.",
    }

    validated = GovernmentJobExtraction.model_validate(sample_govt)
    assert validated.recruitment_organization == "State Bank of India (SBI)"
    assert validated.vacancies_count == 2000
    assert validated.notification_number == "CRPD/PO/2026-27/01"


@pytest.mark.asyncio
async def test_grok_client_baseline_extraction():
    """Verify GrokAIClient fallback parser when API key is unconfigured."""
    client = GrokAIClient()
    res = await client.extract_job_data(
        raw_text="Lead DevOps Engineer\nAmazon Web Services\nBangalore\nRequirements: AWS, Kubernetes, Terraform",
        source_type="PRIVATE",
        fallback_url="https://aws.amazon.com/jobs",
    )
    assert res["job_title"] != ""
    assert res["job_type"] == "PRIVATE"
    assert "application_url" in res
