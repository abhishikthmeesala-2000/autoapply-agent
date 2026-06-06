from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.models import Job, JobRequirement, Profile, User
from app.job_analysis.service import analyze_job_requirements
from app.main import app, get_db_session, get_ollama_client


class FakeOllamaClient:
    def __init__(self, response: dict, model_name: str = "qwen3") -> None:
        self.response = response
        self.config = SimpleNamespace(qwen_model=model_name)
        self.calls: list[dict[str, str]] = []

    def close(self) -> None:
        return None

    def chat_json(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def _create_profile_and_job(db_session) -> tuple[Profile, Job]:
    user = User(email="analysis@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name="Analyzer", location="Remote")
    db_session.add(profile)
    db_session.flush()

    job = Job(
        profile_id=profile.id,
        source="greenhouse",
        source_job_id="101",
        stable_hash="stable-hash-101",
        title="Senior Backend Engineer",
        company="Acme",
        location="Remote",
        description=(
            "Build Python APIs.\n"
            "Required: 5+ years experience, FastAPI, PostgreSQL.\n"
            "Preferred: AWS, Docker.\n"
            "Remote in the United States.\n"
            "Must be authorized to work in the US."
        ),
        apply_url="https://careers.acme.example/jobs/101",
        status="discovered",
    )
    db_session.add(job)
    db_session.commit()
    return profile, job


def test_job_analysis_persists_validated_requirements(db_session) -> None:
    profile, job = _create_profile_and_job(db_session)
    ai_client = FakeOllamaClient(
        {
            "role_summary": "Backend engineer building Python APIs.",
            "must_have_skills": ["FastAPI", "PostgreSQL", "Python"],
            "nice_to_have_skills": ["AWS", "Docker"],
            "responsibilities": ["Build APIs", "Maintain backend services"],
            "experience_requirements": ["5+ years of experience"],
            "education_requirements": [],
            "work_authorization": "Authorized to work in the United States",
            "location_requirement": "Remote",
            "seniority": "Senior",
            "red_flags": ["United States only"],
        },
        model_name="qwen3",
    )

    response = analyze_job_requirements(
        db=db_session,
        profile_id=profile.id,
        job_id=job.id,
        ai_client=ai_client,
    )

    assert response.profile_id == profile.id
    assert response.job_id == job.id
    assert response.analyzed_by == "qwen3"
    assert response.structured_json.role_summary == "Backend engineer building Python APIs."
    assert ai_client.calls[0]["model"] == "qwen3"

    stored = db_session.query(JobRequirement).filter(JobRequirement.job_id == job.id).one()
    assert stored.profile_id == profile.id
    assert stored.analyzed_by == "qwen3"
    assert stored.structured_json["must_have_skills"] == ["FastAPI", "PostgreSQL", "Python"]


def test_job_analysis_endpoint_returns_422_on_schema_mismatch(db_session) -> None:
    profile, job = _create_profile_and_job(db_session)
    ai_client = FakeOllamaClient(
        {
            "must_have_skills": ["FastAPI"],
            "nice_to_have_skills": [],
            "responsibilities": [],
            "experience_requirements": [],
            "education_requirements": [],
            "work_authorization": None,
            "location_requirement": None,
            "seniority": None,
            "red_flags": [],
        }
    )

    def override_db():
        yield db_session

    def override_ai_client():
        yield ai_client

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_ollama_client] = override_ai_client

    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/jobs/{job.id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert db_session.query(JobRequirement).filter(JobRequirement.job_id == job.id).count() == 0


def test_job_analysis_rejects_jobs_from_other_profiles(db_session) -> None:
    profile, job = _create_profile_and_job(db_session)

    other_user = User(email="other@example.com")
    db_session.add(other_user)
    db_session.flush()
    other_profile = Profile(user_id=other_user.id, name="Other", location="Remote")
    db_session.add(other_profile)
    db_session.commit()

    ai_client = FakeOllamaClient(
        {
            "role_summary": "Backend engineer building Python APIs.",
            "must_have_skills": ["FastAPI"],
            "nice_to_have_skills": [],
            "responsibilities": [],
            "experience_requirements": [],
            "education_requirements": [],
            "work_authorization": None,
            "location_requirement": None,
            "seniority": None,
            "red_flags": [],
        }
    )

    def override_db():
        yield db_session

    def override_ai_client():
        yield ai_client

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_ollama_client] = override_ai_client

    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{other_profile.id}/jobs/{job.id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
