from __future__ import annotations

import hashlib
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.db.models import (
    Application,
    AgentRun,
    Job,
    JobRequirement,
    MasterResume,
    Profile,
    ProfileSetting,
    ResumeVersion,
    User,
)
from app.job_analysis.schemas import JobRequirementPayload
from app.main import app, get_db_session, get_job_discovery_client


def _create_profile(
    db_session,
    *,
    max_applications_per_day: int = 5,
    active: bool = True,
) -> Profile:
    user = User(email=f"agent-{uuid4().hex}@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name="Agent", location="Remote")
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=["backend engineer"],
            locations=["Remote"],
            excluded_roles=[],
            job_sources=["https://boards-api.greenhouse.io/v1/boards/acme/jobs?content=true"],
            match_threshold=70,
            max_applications_per_day=max_applications_per_day,
            active=active,
        )
    )
    db_session.commit()
    return profile


def _stable_hash(source_job_id: str) -> str:
    return hashlib.sha256(source_job_id.strip().lower().encode("utf-8")).hexdigest()


def _create_discovered_job(db_session, profile_id: str) -> Job:
    job = Job(
        profile_id=profile_id,
        source="greenhouse",
        source_job_id="101",
        stable_hash=_stable_hash("101"),
        title="Senior Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build Python APIs with FastAPI and 5+ years of experience.",
        apply_url="https://careers.acme.example/jobs/101",
        status="discovered",
    )
    db_session.add(job)
    db_session.commit()
    return job


def _create_requirement(db_session, profile_id: str, job_id: str) -> None:
    requirement = JobRequirementPayload(
        role_summary="Backend engineer building Python APIs.",
        must_have_skills=["Python", "FastAPI"],
        nice_to_have_skills=["Docker"],
        responsibilities=["Build APIs"],
        experience_requirements=["5+ years of experience"],
        education_requirements=[],
        work_authorization="Must be authorized to work in the United States.",
        location_requirement="Remote",
        seniority="Senior",
        red_flags=[],
    )
    db_session.add(
        JobRequirement(
            profile_id=profile_id,
            job_id=job_id,
            structured_json=requirement.model_dump(mode="json"),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()


def _create_resume_and_version(db_session, profile_id: str, job_id: str) -> ResumeVersion:
    master_resume = MasterResume(
        profile_id=profile_id,
        file_name="resume.docx",
        source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        raw_text=(
            "Backend engineer with 7 years of experience in Python, FastAPI, and Docker."
        ),
        parsed_json={"sections": []},
    )
    db_session.add(master_resume)
    db_session.flush()

    payload = {
        "profile_id": profile_id,
        "job_id": job_id,
        "job_match_id": str(uuid4()),
        "master_resume_id": master_resume.id,
        "version_number": 1,
        "generated_by": "rule-based-evidence-tailoring",
        "matched_requirements": ["Python", "FastAPI"],
        "unmet_requirements": [],
        "selected_evidence_ids": [],
        "sections": [],
    }
    version = ResumeVersion(
        profile_id=profile_id,
        job_id=job_id,
        master_resume_id=master_resume.id,
        version_number=1,
        file_name="tailored.json",
        tailored_json=payload,
        ats_score=90.0,
    )
    db_session.add(version)
    db_session.commit()
    return version


def _mock_discovery_client() -> httpx.Client:
    def responder(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "boards-api.greenhouse.io" in url:
            return httpx.Response(
                200,
                json={
                    "company_name": "Acme",
                    "jobs": [
                        {
                            "id": 101,
                            "title": "Senior Backend Engineer",
                            "content": "Build Python APIs with FastAPI and 5+ years of experience.",
                            "location": {"name": "Remote"},
                            "absolute_url": "https://careers.acme.example/jobs/101",
                        }
                    ],
                },
            )

        return httpx.Response(404, json={"error": "not found"})

    return httpx.Client(transport=httpx.MockTransport(responder), base_url="https://example.com")


def _override_db(db_session):
    def _yield():
        yield db_session

    return _yield


def _override_client():
    client = _mock_discovery_client()

    def _yield():
        try:
            yield client
        finally:
            client.close()

    return _yield


def test_agent_start_discovers_scores_and_prepares_draft_application(db_session) -> None:
    profile = _create_profile(db_session)
    job = _create_discovered_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)
    resume_version = _create_resume_and_version(db_session, profile.id, job.id)

    app.dependency_overrides[get_db_session] = _override_db(db_session)
    app.dependency_overrides[get_job_discovery_client] = _override_client()
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/agent/start")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == profile.id
    assert body["status"] == "running"
    assert body["metadata"]["jobs_discovered"] == 1
    assert body["metadata"]["jobs_scored"] == 1
    assert body["metadata"]["applications_prepared"] == 1
    assert body["metadata"]["daily_limit_reached"] is False

    stored_application = db_session.query(Application).filter(Application.profile_id == profile.id).one()
    assert stored_application.job_id == job.id
    assert stored_application.resume_version_id == resume_version.id
    assert stored_application.status == "draft"
    assert stored_application.approval_required is True


def test_agent_pause_and_stop_update_run_state(db_session) -> None:
    profile = _create_profile(db_session)
    job = _create_discovered_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)
    _create_resume_and_version(db_session, profile.id, job.id)

    app.dependency_overrides[get_db_session] = _override_db(db_session)
    app.dependency_overrides[get_job_discovery_client] = _override_client()
    try:
        with TestClient(app) as client:
            start_response = client.post(f"/profiles/{profile.id}/agent/start")
            pause_response = client.post(f"/profiles/{profile.id}/agent/pause")
            stop_response = client.post(f"/profiles/{profile.id}/agent/stop")
    finally:
        app.dependency_overrides.clear()

    assert start_response.status_code == 200
    assert pause_response.status_code == 200
    assert stop_response.status_code == 200
    assert pause_response.json()["status"] == "paused"
    assert stop_response.json()["status"] == "stopped"
    assert stop_response.json()["ended_at"] is not None


def test_agent_start_respects_daily_application_limit(db_session) -> None:
    profile = _create_profile(db_session, max_applications_per_day=1)
    job = _create_discovered_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)
    _create_resume_and_version(db_session, profile.id, job.id)

    other_job = Job(
        profile_id=profile.id,
        source="greenhouse",
        source_job_id="102",
        stable_hash=_stable_hash("102"),
        title="Platform Engineer",
        company="Acme",
        location="Remote",
        description="Infrastructure work.",
        apply_url="https://careers.acme.example/jobs/102",
        status="discovered",
    )
    db_session.add(other_job)
    db_session.flush()
    db_session.add(
        Application(
            profile_id=profile.id,
            job_id=other_job.id,
            status="draft",
            approval_required=True,
        )
    )
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_db(db_session)
    app.dependency_overrides[get_job_discovery_client] = _override_client()
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/agent/start")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["applications_prepared"] == 0
    assert body["metadata"]["daily_limit_reached"] is True
    assert any("Daily application limit reached." in note for note in body["metadata"]["notes"])
    assert (
        db_session.query(Application).filter(Application.profile_id == profile.id).count()
        == 1
    )


def test_agent_start_is_idempotent_for_existing_draft_application(db_session) -> None:
    profile = _create_profile(db_session)
    job = _create_discovered_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)
    _create_resume_and_version(db_session, profile.id, job.id)

    app.dependency_overrides[get_db_session] = _override_db(db_session)
    app.dependency_overrides[get_job_discovery_client] = _override_client()
    try:
        with TestClient(app) as client:
            first_response = client.post(f"/profiles/{profile.id}/agent/start")
            second_response = client.post(f"/profiles/{profile.id}/agent/start")
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert (
        db_session.query(Application).filter(Application.profile_id == profile.id).count()
        == 1
    )
    assert db_session.query(AgentRun).filter(AgentRun.profile_id == profile.id).count() == 2
