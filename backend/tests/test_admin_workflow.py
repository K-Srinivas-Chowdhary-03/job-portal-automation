import uuid
import pytest
from httpx import AsyncClient
from app.models.job import Job
from app.models.job import Job as JobModel
from app.models.user import User
from app.schemas.job import JobUpdate

@pytest.mark.asyncio
async def test_admin_can_access_dashboard(client: AsyncClient, admin_user: dict):
    token = admin_user["token"]
    response = await client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    # basic keys exist
    for key in ["total_published", "pending_jobs", "approved_jobs", "rejected_jobs"]:
        assert key in data

@pytest.mark.asyncio
async def test_regular_user_forbidden_dashboard(client: AsyncClient, regular_user: dict):
    token = regular_user["token"]
    response = await client.get("/api/v1/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_unauthenticated_dashboard_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_admin_lists_pending_jobs(client: AsyncClient, admin_user: dict, db_session):
    # create a pending job
    job = Job(
        id=uuid.uuid4(),
        title="Test Job",
        slug="test-job",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.get("/api/v1/admin/jobs/pending", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert any(j["id"] == str(job.id) for j in data)

@pytest.mark.asyncio
async def test_admin_retrieves_job_detail(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Detail Job",
        slug="detail-job",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.get(f"/api/v1/admin/jobs/{job.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["job"]["id"] == str(job.id)

@pytest.mark.asyncio
async def test_admin_edits_job_details(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Old Title",
        slug="old-title",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    update_payload = {"title": "New Title", "location": "NYC"}
    resp = await client.patch(
        f"/api/v1/admin/jobs/{job.id}", json=update_payload, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["location"] == "NYC"

@pytest.mark.asyncio
async def test_admin_approves_pending_job(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Approve Me",
        slug="approve-me",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.post(
        f"/api/v1/admin/jobs/{job.id}/approve", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"

@pytest.mark.asyncio
async def test_admin_rejects_pending_job(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Reject Me",
        slug="reject-me",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.post(
        f"/api/v1/admin/jobs/{job.id}/reject", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"

@pytest.mark.asyncio
async def test_admin_publishes_approved_job(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Publish Me",
        slug="publish-me",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="APPROVED",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.post(
        f"/api/v1/admin/jobs/{job.id}/publish", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PUBLISHED"

@pytest.mark.asyncio
async def test_publish_pending_job_invalid_transition(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Bad Publish",
        slug="bad-publish",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.post(
        f"/api/v1/admin/jobs/{job.id}/publish", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_approve_rejected_job_invalid_transition(client: AsyncClient, admin_user: dict, db_session):
    job = Job(
        id=uuid.uuid4(),
        title="Already Rejected",
        slug="already-rejected",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="REJECTED",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    resp = await client.post(
        f"/api/v1/admin/jobs/{job.id}/approve", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_audit_history_records_actions(client: AsyncClient, admin_user: dict, db_session):
    # create pending job then approve and publish
    job = Job(
        id=uuid.uuid4(),
        title="Audit Test",
        slug="audit-test",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add(job)
    await db_session.commit()
    token = admin_user["token"]
    # approve
    await client.post(f"/api/v1/admin/jobs/{job.id}/approve", headers={"Authorization": f"Bearer {token}"})
    # publish
    await client.post(f"/api/v1/admin/jobs/{job.id}/publish", headers={"Authorization": f"Bearer {token}"})
    # fetch audit history via raw job detail endpoint (includes audit via separate endpoint not present, so we query directly)
    # Use direct DB query
    result = await db_session.execute(
        "SELECT action FROM job_review_history WHERE job_id = :jid ORDER BY created_at", {"jid": str(job.id)}
    )
    actions = [row[0] for row in result.fetchall()]
    assert "APPROVE" in actions and "PUBLISH" in actions

@pytest.mark.asyncio
async def test_public_job_listing_returns_only_published(client: AsyncClient, db_session):
    # create a published job and a pending job
    pub_job = Job(
        id=uuid.uuid4(),
        title="Public Job",
        slug="public-job",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PUBLISHED",
    )
    pend_job = Job(
        id=uuid.uuid4(),
        title="Hidden Job",
        slug="hidden-job",
        description="desc",
        job_type="PRIVATE",
        employment_type="FULL_TIME",
        location="Remote",
        application_url="https://example.com/apply",
        status="PENDING",
    )
    db_session.add_all([pub_job, pend_job])
    await db_session.commit()
    # public jobs endpoint is likely /api/v1/jobs (list) – use that
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    data = resp.json()
    ids = [item["id"] for item in data]
    assert str(pub_job.id) in ids
    assert str(pend_job.id) not in ids
