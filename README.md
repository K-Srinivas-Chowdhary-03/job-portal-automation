# Automated Job Notification Platform

An AI-powered, production-ready Job Notification Aggregation Platform that collects job notifications from private MNCs, startups, and official government recruitment portals, processes them through Grok AI (xAI API) for structured extraction, enforces an administrative review & approval workflow, and publishes verified jobs to a high-performance Next.js web application.

---

## 🛠 Technology Stack

- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS, Lucide React, Axios
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (Async/Sync), Alembic, Pydantic v2
- **Scraping**: BeautifulSoup4, HTTPX, Playwright (Headless Chromium)
- **AI Processing**: Grok AI (xAI API) with JSON schema extraction
- **Background Tasks**: Celery, Celery Beat, Redis
- **Database**: PostgreSQL with UUID primary keys & JSONB metadata
- **Containerization**: Docker, Docker Compose

---

## 🏗 Architecture & Core Principles

```
Scraper Engine (BS4 / Playwright)
  ├──> Archives raw HTML to `raw_job_records`
  ├──> Grok AI extracts structured fields (Private / Govt schemas)
  ├──> Pydantic validates data (no hallucinations allowed)
  ├──> Duplicate Detection (External ID, Canonical URL, SHA256 Fingerprint)
  └──> Inserts into `jobs` table strictly as status = 'PENDING'
          │
          ▼
Admin Review Dashboard
  ├──> Compares Grok JSON against raw scraped HTML
  ├──> Inline edits and data corrections
  ├──> Explicit Action: Approve (moves to 'APPROVED')
  └──> Explicit Action: Publish (moves to 'PUBLISHED')
          │
          ▼
Public Next.js Portal
  └──> Only status = 'PUBLISHED' vacancies are accessible to users
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ / 22+
- PostgreSQL & Redis (or Docker)

### 2. Environment Configuration
Copy `.env.example` to both root and `backend/.env`:
```bash
cp .env.example backend/.env
```
Ensure your database credentials and `XAI_API_KEY` are populated.

### 3. Backend Setup
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
playwright install chromium
```

Run Alembic database migrations:
```bash
alembic upgrade head
```

Seed initial categories, skills, and Super Admin:
```bash
python app/seed.py
```
*(Default Super Admin: `admin@jobportal.local` / `Admin@123456`)*

Start FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive API Documentation will be available at: `http://localhost:8000/api/v1/docs`

### 4. Background Workers (Celery & Beat)
In separate terminals:
```bash
# Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info

# Celery Beat (Scheduler)
celery -A app.tasks.celery_app beat --loglevel=info
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing

Run backend test suite:
```bash
cd backend
pytest -v
```

Run frontend production build verification:
```bash
cd frontend
npm run build
```

---

## 🛡 Security & Audit Trail
- Every administrative action (Approve, Reject, Publish, Edit) is permanently audited in `job_review_history`.
- Application URLs are canonicalized to strip tracking tokens and verify genuine employer endpoints.
- Scraping, extraction, and publication are strictly isolated; AI can never publish directly.
