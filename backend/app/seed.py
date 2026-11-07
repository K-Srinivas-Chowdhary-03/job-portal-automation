"""Seed initial categories, sample skills, and superadmin account."""
import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import Category, User, Skill


INITIAL_CATEGORIES = [
    {"name": "Software Development", "slug": "software-development", "job_type": "PRIVATE"},
    {"name": "Frontend Development", "slug": "frontend-development", "job_type": "PRIVATE"},
    {"name": "Backend Development", "slug": "backend-development", "job_type": "PRIVATE"},
    {"name": "Full Stack Development", "slug": "full-stack-development", "job_type": "PRIVATE"},
    {"name": "Testing & QA", "slug": "testing-qa", "job_type": "PRIVATE"},
    {"name": "DevOps & Cloud", "slug": "devops-cloud", "job_type": "PRIVATE"},
    {"name": "Data Science & AI", "slug": "data-science-ai", "job_type": "PRIVATE"},
    {"name": "Banking & Finance", "slug": "banking-finance", "job_type": "BOTH"},
    {"name": "Railway", "slug": "railway", "job_type": "GOVERNMENT"},
    {"name": "Teaching & Education", "slug": "teaching-education", "job_type": "BOTH"},
    {"name": "Government Administration", "slug": "government-administration", "job_type": "GOVERNMENT"},
    {"name": "Defense & Police", "slug": "defense-police", "job_type": "GOVERNMENT"},
    {"name": "Other", "slug": "other", "job_type": "BOTH"},
]

INITIAL_SKILLS = [
    "Python", "FastAPI", "Django", "JavaScript", "TypeScript", "React", "Next.js",
    "Node.js", "Java", "Spring Boot", "C++", "C#", ".NET", "SQL", "PostgreSQL",
    "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux",
    "Git", "REST API", "GraphQL", "Machine Learning", "Data Analysis"
]


async def seed_database():
    async with AsyncSessionLocal() as session:
        # 1. Seed Categories
        print("[*] Seeding categories...")
        for cat_data in INITIAL_CATEGORIES:
            result = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                category = Category(
                    id=uuid.uuid4(),
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    job_type=cat_data["job_type"],
                )
                session.add(category)
        
        # 2. Seed Skills
        print("[*] Seeding skills...")
        for skill_name in INITIAL_SKILLS:
            result = await session.execute(
                select(Skill).where(Skill.name == skill_name)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                skill = Skill(
                    id=uuid.uuid4(),
                    name=skill_name,
                )
                session.add(skill)

        # 3. Seed Super Admin
        admin_email = "admin@jobportal.com"
        print(f"[*] Checking Super Admin account ({admin_email})...")
        result = await session.execute(
            select(User).where(User.email == admin_email)
        )
        existing_admin = result.scalar_one_or_none()
        if not existing_admin:
            admin_user = User(
                id=uuid.uuid4(),
                name="Platform Administrator",
                email=admin_email,
                password_hash=get_password_hash("Admin@123456"),
                role="ADMIN",
                is_active=True,
            )
            session.add(admin_user)
            print(f"[+] Created Super Admin: {admin_email} (Password: Admin@123456)")
        else:
            print(f"[-] Super Admin already exists: {admin_email}")

        await session.commit()
        print("[OK] Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
