from __future__ import annotations

from fastapi.testclient import TestClient

from app.browser_jobs.schemas import BrowserJobPayload
from app.browser_jobs.service import receive_browser_job
from app.db.models import Job, Profile, User
from app.main import app, get_db_session


def _create_profile(db_session) -> Profile:
    user = User(email="browser-jobs@example.com")
    db_session.add(user)
    db_session.flush()
    profile = Profile(user_id=user.id, name="Browser", location="Remote")
    db_session.add(profile)
    db_session.commit()
    return profile


def test_browser_job_ingestion_persists_profile_scoped_job(db_session) -> None:
    profile = _create_profile(db_session)
    payload = BrowserJobPayload(
        profile_id=profile.id,
        source="greenhouse",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build APIs.",
        apply_url="https://careers.acme.example/jobs/1",
        page_url="https://careers.acme.example/jobs/1",
    )

    response = receive_browser_job(db=db_session, payload=payload)

    assert response.status == "received"
    jobs = db_session.query(Job).filter(Job.profile_id == profile.id).all()
    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].profile_id == profile.id


def test_browser_job_ingestion_dedupes_per_profile(db_session) -> None:
    profile = _create_profile(db_session)
    payload = BrowserJobPayload(
        profile_id=profile.id,
        source="greenhouse",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build APIs.",
        apply_url="https://careers.acme.example/jobs/1",
        page_url="https://careers.acme.example/jobs/1",
    )

    receive_browser_job(db=db_session, payload=payload)
    receive_browser_job(db=db_session, payload=payload)

    jobs = db_session.query(Job).filter(Job.profile_id == profile.id).all()
    assert len(jobs) == 1


def test_browser_job_path_profile_mismatch_rejected(db_session) -> None:
    profile = _create_profile(db_session)
    payload = BrowserJobPayload(
        profile_id=profile.id,
        source="lever",
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build APIs.",
        apply_url="https://jobs.lever.co/acme/1",
        page_url="https://jobs.lever.co/acme/1",
    )

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        client = TestClient(app)
        response = client.post(
            f"/profiles/{profile.id}/jobs/extracted",
            json={**payload.model_dump(mode="json"), "profile_id": "mismatch"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
