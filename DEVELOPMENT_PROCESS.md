# Development Process for Job Portal Automation

## Overview
This document outlines the **step‑by‑step development workflow** for the Job Portal Automation project when running locally with Docker. It captures the required **manual actions** you must perform before any automated changes are applied, and it defines the order in which phases should be completed.

---

## 1️⃣ Prerequisites (One‑time setup)
1. **Docker Desktop & Docker Compose**
   - Install Docker Desktop for Windows and verify `docker compose version` works.
2. **Python & Node environments** (only needed for local builds / tooling)
   - Python 3.12 (or use the Docker image for runtime).
   - Node 22 (or use the Docker image for the frontend).
3. **Clone the repository** and open a terminal at `d:\Job Portal-Automation`.
4. **Create environment files**
   - **Backend**: copy the template to a real env file.
     ```powershell
     cp backend\.env.example backend\.env   # edit the file afterwards
     ```
   - **Frontend** (optional, only if you ever run `npm run dev` outside Docker):
     ```powershell
     cp frontend\.env.example frontend\.env   # not required for Docker
     ```
5. **Populate the backend `.env`** with your local credentials (use the placeholder values from the template unless you changed the defaults):
   ```text
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_DB=job_portal_db
   POSTGRES_HOST=postgres
   POSTGRES_PORT=5432

   REDIS_URL=redis://redis:6379/0

   XAI_API_KEY=YOUR_XAI_KEY_HERE
   XAI_BASE_URL=https://api.x.ai
   XAI_MODEL=grok-beta

   # Optional – if you ever need to override the Playwright binary location inside the container
   # PLAYWRIGHT_EXECUTABLE_PATH=/path/inside/container/chrome
   ```
6. **Create an admin user** (if none exists) so the admin API can be exercised later:
   ```powershell
   docker compose exec postgres psql -U postgres -d job_portal_db -c "INSERT INTO users (id, email, hashed_password, is_active, is_admin) VALUES (gen_random_uuid(), 'admin@example.com', crypt('adminpass', gen_salt('bf')), true, true);"
   ```
   - After the user exists, obtain a JWT by calling the login endpoint (`POST http://localhost:8000/api/v1/auth/login`). Save the token – you will need it for the admin‑workflow tests.

---

## 2️⃣ Phase 2 – Playwright Integration (backend)
> **Goal:** Verify that Chromium works inside the backend container and that the scraper can launch, navigate, and clean up.

### Manual actions before code changes
1. **Build the backend image once** (this will also install Playwright and Chromium):
   ```powershell
   docker compose build backend
   ```
2. **Run a quick sanity check** that Playwright can locate Chromium inside the container:
   ```powershell
   docker compose run --rm backend bash -c "python -c \"from app.utils.playwright_path import get_chromium_executable; print(get_chromium_executable())\""
   ```
   - The command should print a path ending in `chrome` (e.g., `/root/.cache/ms-playwright/chromium-<ver>/chrome-win64/chrome.exe`). If it raises `FileNotFoundError`, the installation step failed and you must reinstall Playwright inside the image.
3. **Keep the JWT token** from step 1‑6 of the prerequisites; it will be needed for the admin‑review tests that follow.

### Automated steps (will be executed after you approve)
- Apply the Playwright launch‑path changes in `generic_playwright.py`.
- Add timeout handling (`asyncio.wait_for`) and a `finally` block to guarantee `browser.close()`.
- Run the prepared unit test `tests/test_playwright_scraper.py` inside the container and capture the results.

---

## 3️⃣ Phase 2 – Admin Review Workflow (backend)
> **Goal:** Provide secure admin endpoints for reviewing, editing, approving, rejecting, and publishing jobs.

### Manual actions before code changes
1. **Make sure the admin JWT token** from the prerequisites is handy (you’ll paste it into the test suite).
2. **Confirm the backend `.env`** is loaded by Docker (the `env_file:` line in `docker‑compose.yml` points to `./backend/.env`).

### Automated steps (after Playwright verification)
- Create API routes under `backend/app/api/v1/admin_jobs.py`.
- Add corresponding Pydantic schemas in `backend/app/schemas/admin.py`.
- Insert audit rows (`JobReviewHistory`) on each status change.
- Write and run backend tests (`tests/test_admin_workflow.py`).
- Update `DEVELOPMENT_PROGRESS.md` with the results.

---

## 4️⃣ Phase 3 – Docker Compose Enhancements (dev vs prod)
> **Goal:** Provide a clean development setup and an optimized production configuration without duplicating services.

### Manual actions before changes
1. **Decide on a production start command** (e.g., `uvicorn app.main:app --workers 4`).
2. **Create a production override file** (optional, but recommended):
   - `docker-compose.prod.yml` that:
     - Removes `--reload` from the backend command.
     - Sets `environment: - NODE_ENV=production` for the frontend (already present).
     - Adds a basic health‑check for the backend (`curl http://localhost:8000/health`).
   - This file will be used later with:
     ```powershell
     docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
     ```
3. **Backup the existing PostgreSQL volume** (just in case you ever need to restore):
   ```powershell
   docker run --rm -v job_portal_postgres:/var/lib/postgresql/data -v %cd%/backup:/backup alpine tar czf /backup/postgres_backup.tar.gz -C /var/lib/postgresql/data .
   ```
   - Keep the `backup` folder safe; you can restore with a similar `tar xzf` command.

### Automated steps (after approval)
- No code changes are required for the compose file itself; we will only add the optional `docker-compose.prod.yml` and health‑checks.
- Update `DEVELOPMENT_PROGRESS.md` with the new Docker files and the backup verification.

---

## 5️⃣ Phase 4 – Comprehensive Testing
> **Goal:** Run integration, security, performance, concurrency, and recovery tests covering the full workflow.

### Manual actions before automated tests
1. **Ensure the admin JWT token** is still valid (login again if needed).
2. **Make sure the backend image is rebuilt** after any code changes (the CI pipeline will do this automatically, but for local work run `docker compose build backend`).
3. **Start the full stack** (dev mode) after any code change:
   ```powershell
   docker compose up -d
   ```
   - Wait for the health‑checks on PostgreSQL and Redis to pass (you can monitor with `docker compose ps`).
4. **Optionally seed some test data** (e.g., run a script that inserts a few `RawJobRecord` rows) to have something for the integration test to process.

### Automated steps (after you give the go‑ahead)
- Run the full pytest suite (`docker compose exec backend pytest -q`).
- Run performance tests with `locust` or a simple script that spawns multiple Celery scrape tasks.
- Simulate a worker crash (`docker compose stop celery_worker`), then restart and verify the task is retried.
- Verify that `/api/v1/jobs` returns **only** `PUBLISHED` jobs after the full workflow.
- Document all results and update `DEVELOPMENT_PROGRESS.md`.

---

## 6️⃣ Ongoing Documentation & Reporting
- After **each sub‑phase** (Playwright fix, admin API, Docker tweaks, testing) the `DEVELOPMENT_PROGRESS.md` file will be appended with:
  - What was changed.
  - Test command(s) run.
  - Real test output (pass/fail, counts, timings).
  - Any new manual actions required for the next step.

---

## 7️⃣ Summary of Manual Actions You Must Perform **Before I Continue**
1. Create `backend/.env` from a template (populate with real DB, Redis, XAI credentials).<br>
2. (Optional) Create `frontend/.env` if you ever run the UI outside Docker.
3. Build the backend Docker image once (`docker compose build backend`).
4. Verify Playwright Chromium inside the container (run the `get_chromium_executable()` command).<br>
5. Create an admin user in PostgreSQL (SQL INSERT shown above).<br>
6. Obtain a JWT token for that admin user (login via the API).<br>
7. (Optional) Prepare `docker-compose.prod.yml` if you want a production‑ready compose file now.<br>
8. (Optional) Back up the PostgreSQL volume if you ever need a safety copy.

Once you confirm these steps are done (or let me know where you need help), I will proceed with the **Phase 2** code updates, run the Playwright test, and then move on to the admin‑review workflow.
