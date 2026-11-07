"""Seed real Indian job sources (IT companies + Government portals) into the database."""
import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.source import Source


PRIVATE_IT_SOURCES = [
    {
        "name": "TCS Careers",
        "source_url": "https://www.tcs.com/careers/tcs-careers",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "TCS", "job_type": "PRIVATE"},
    },
    {
        "name": "Infosys Careers",
        "source_url": "https://www.infosys.com/careers/apply.html",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Infosys", "job_type": "PRIVATE"},
    },
    {
        "name": "Wipro Careers",
        "source_url": "https://careers.wipro.com/careers-home/",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Wipro", "job_type": "PRIVATE"},
    },
    {
        "name": "HCL Technologies Careers",
        "source_url": "https://www.hcltech.com/careers",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "HCL", "job_type": "PRIVATE"},
    },
    {
        "name": "Accenture India Careers",
        "source_url": "https://www.accenture.com/in-en/careers",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Accenture", "job_type": "PRIVATE"},
    },
    {
        "name": "Cognizant Careers",
        "source_url": "https://careers.cognizant.com/global/en",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Cognizant", "job_type": "PRIVATE"},
    },
    {
        "name": "Tech Mahindra Careers",
        "source_url": "https://careers.techmahindra.com/",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Tech Mahindra", "job_type": "PRIVATE"},
    },
    {
        "name": "Capgemini Careers India",
        "source_url": "https://www.capgemini.com/in-en/careers/",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 120,
        "config": {"company": "Capgemini", "job_type": "PRIVATE"},
    },
    {
        "name": "IBM India Careers",
        "source_url": "https://www.ibm.com/in-en/employment/",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 180,
        "config": {"company": "IBM", "job_type": "PRIVATE"},
    },
    {
        "name": "Amazon India Jobs",
        "source_url": "https://www.amazon.jobs/en/locations/india",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 60,
        "config": {"company": "Amazon", "job_type": "PRIVATE"},
    },
    {
        "name": "Google India Jobs",
        "source_url": "https://careers.google.com/jobs/results/?location=India",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 180,
        "config": {"company": "Google", "job_type": "PRIVATE"},
    },
    {
        "name": "Microsoft India Careers",
        "source_url": "https://jobs.careers.microsoft.com/global/en/search?lc=India",
        "source_type": "PRIVATE",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 180,
        "config": {"company": "Microsoft", "job_type": "PRIVATE"},
    },
    {
        "name": "Freshersworld - IT Jobs",
        "source_url": "https://www.freshersworld.com/jobs/it-software-jobs",
        "source_type": "PRIVATE",
        "scraper_type": "HTML",
        "schedule_minutes": 60,
        "config": {"job_type": "PRIVATE", "selector": ".job-container"},
    },
]

GOVERNMENT_SOURCES = [
    {
        "name": "UPSC Official Recruitment",
        "source_url": "https://upsc.gov.in/recruitment",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 240,
        "config": {"job_type": "GOVERNMENT", "department": "UPSC"},
    },
    {
        "name": "SSC - Staff Selection Commission",
        "source_url": "https://ssc.nic.in/",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 240,
        "config": {"job_type": "GOVERNMENT", "department": "SSC"},
    },
    {
        "name": "Indian Railways Recruitment (RRC/RRB)",
        "source_url": "https://indianrailways.gov.in/railwayboard/view_section.jsp?lang=0&id=0,1,304,366,533",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 240,
        "config": {"job_type": "GOVERNMENT", "department": "Railway"},
    },
    {
        "name": "IBPS - Bank Jobs",
        "source_url": "https://www.ibps.in/",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 240,
        "config": {"job_type": "GOVERNMENT", "department": "Banking"},
    },
    {
        "name": "SBI Careers",
        "source_url": "https://bank.sbi/web/careers",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 240,
        "config": {"job_type": "GOVERNMENT", "department": "SBI"},
    },
    {
        "name": "DRDO Recruitment",
        "source_url": "https://www.drdo.gov.in/careers",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 360,
        "config": {"job_type": "GOVERNMENT", "department": "DRDO"},
    },
    {
        "name": "ISRO Recruitment",
        "source_url": "https://www.isro.gov.in/Careers.html",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 360,
        "config": {"job_type": "GOVERNMENT", "department": "ISRO"},
    },
    {
        "name": "NHM - National Health Mission",
        "source_url": "https://nhm.gov.in/index1.php?lang=1&level=1&sublinkid=971&lid=154",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 360,
        "config": {"job_type": "GOVERNMENT", "department": "Health"},
    },
    {
        "name": "Naukri Government Jobs",
        "source_url": "https://www.naukri.com/government-jobs",
        "source_type": "GOVERNMENT",
        "scraper_type": "PLAYWRIGHT",
        "schedule_minutes": 60,
        "config": {"job_type": "GOVERNMENT"},
    },
    {
        "name": "FreeJobAlert - All Govt Jobs",
        "source_url": "https://www.freejobalert.com/latest-notifications/",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 60,
        "config": {"job_type": "GOVERNMENT"},
    },
    {
        "name": "Sarkari Result",
        "source_url": "https://www.sarkariresult.com/latest-jobs/",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 60,
        "config": {"job_type": "GOVERNMENT"},
    },
    {
        "name": "Employment News India",
        "source_url": "https://www.employmentnews.gov.in/",
        "source_type": "GOVERNMENT",
        "scraper_type": "HTML",
        "schedule_minutes": 120,
        "config": {"job_type": "GOVERNMENT"},
    },
]

ALL_SOURCES = PRIVATE_IT_SOURCES + GOVERNMENT_SOURCES


async def seed_sources():
    async with AsyncSessionLocal() as session:
        print(f"[*] Seeding {len(ALL_SOURCES)} job sources...")
        added = 0
        skipped = 0

        for src_data in ALL_SOURCES:
            result = await session.execute(
                select(Source).where(Source.source_url == src_data["source_url"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                source = Source(
                    id=uuid.uuid4(),
                    name=src_data["name"],
                    source_url=src_data["source_url"],
                    source_type=src_data["source_type"],
                    scraper_type=src_data["scraper_type"],
                    schedule_minutes=src_data["schedule_minutes"],
                    config=src_data.get("config", {}),
                    is_active=True,
                )
                session.add(source)
                added += 1
                print(f"  [+] {src_data['source_type']:12s} | {src_data['name']}")
            else:
                skipped += 1
                print(f"  [-] Already exists: {src_data['name']}")

        await session.commit()
        print(f"\n[OK] Done! Added {added} new sources, skipped {skipped} existing.")
        print(f"[OK] Total sources now: {added + skipped}")


if __name__ == "__main__":
    asyncio.run(seed_sources())
