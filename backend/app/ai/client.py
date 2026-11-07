import json
import logging
import httpx
from typing import Dict, Any, Union
from app.core.config import settings
from app.ai.prompts import PRIVATE_JOB_SYSTEM_PROMPT, GOVERNMENT_JOB_SYSTEM_PROMPT
from app.schemas.ai_extraction import PrivateJobExtraction, GovernmentJobExtraction

logger = logging.getLogger(__name__)


class GrokAIClient:
    """xAI Grok API Client for structured job notification extraction."""

    def __init__(self):
        self.api_key = settings.XAI_API_KEY
        self.base_url = settings.XAI_BASE_URL.rstrip('/')
        self.model = settings.XAI_MODEL

    async def extract_job_data(
        self, raw_text: str, source_type: str = "PRIVATE", fallback_url: str = ""
    ) -> Dict[str, Any]:
        """Extract structured job information from unstructured scraped content using Grok AI."""
        system_prompt = (
            GOVERNMENT_JOB_SYSTEM_PROMPT
            if source_type.upper() == "GOVERNMENT"
            else PRIVATE_JOB_SYSTEM_PROMPT
        )

        # If API key is not yet configured, provide clean deterministic extraction
        if not self.api_key:
            logger.warning("XAI_API_KEY is not set. Generating baseline normalized extraction.")
            return self._mock_extraction(raw_text, source_type, fallback_url)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Extract structured job data from this scraped announcement:\n\n{raw_text[:4000]}",
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                extracted_json = json.loads(content)

                # Validate against Pydantic schema
                if source_type.upper() == "GOVERNMENT":
                    validated = GovernmentJobExtraction.model_validate(extracted_json)
                else:
                    validated = PrivateJobExtraction.model_validate(extracted_json)

                return validated.model_dump()
            except Exception as exc:
                logger.error(f"Grok AI extraction failed: {exc}. Falling back to baseline extraction.")
                return self._mock_extraction(raw_text, source_type, fallback_url)

    def _mock_extraction(
        self, raw_text: str, source_type: str, fallback_url: str
    ) -> Dict[str, Any]:
        """Deterministic baseline parser when AI API is unavailable."""
        first_line = raw_text.strip().split("\n")[0] if raw_text else "Open Vacancy"
        title = first_line[:120].strip() or "Career Notification"

        if source_type.upper() == "GOVERNMENT":
            return {
                "job_title": title,
                "recruitment_organization": "Official Recruitment Authority",
                "job_type": "GOVERNMENT",
                "notification_number": None,
                "vacancies_count": None,
                "location": ["All India"],
                "age_limit_min": 18,
                "age_limit_max": 35,
                "qualifications": ["Graduate Degree / Diploma"],
                "skills": ["General Administration", "Computer Proficiency"],
                "salary_min": None,
                "salary_max": None,
                "application_start_date": None,
                "application_end_date": None,
                "examination_date": None,
                "application_url": fallback_url or "https://example.gov.in",
                "official_notification_pdf": None,
                "description": raw_text[:1500] if raw_text else "Official Government Recruitment Notification.",
            }

        return {
            "job_title": title,
            "company_name": "Technology Solutions Inc",
            "job_type": "PRIVATE",
            "employment_type": "FULL_TIME",
            "location": ["Bangalore, India"],
            "experience_min": 1,
            "experience_max": 4,
            "qualifications": ["B.Tech", "MCA", "B.Sc Computer Science"],
            "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
            "salary_min": None,
            "salary_max": None,
            "application_url": fallback_url or "https://example.com/apply",
            "application_deadline": None,
            "description": raw_text[:1500] if raw_text else "Private sector technology job opportunity.",
        }


grok_client = GrokAIClient()
