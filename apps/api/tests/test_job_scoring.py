from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import (
    AnswerBank,
    Job,
    JobMatch,
    JobRequirement,
    MasterResume,
    Profile,
    ProfileSetting,
    User,
)
from app.job_analysis.schemas import JobRequirementPayload
from app.job_scoring.service import score_job_for_profile
from app.main import app, get_db_session


def _create_profile(db_session, *, target_roles: list[str], locations: list[str], excluded_roles: list[str], match_threshold: int = 70) -> Profile:
    user = User(email=f"scoring-{uuid4().hex}@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name="Scoring", location="Remote")
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=target_roles,
            locations=locations,
            excluded_roles=excluded_roles,
            job_sources=["https://jobs.example.com"],
            match_threshold=match_threshold,
            max_applications_per_day=5,
        )
    )
    db_session.commit()
    return profile


def _create_resume(db_session, profile_id: str, raw_text: str) -> MasterResume:
    resume = MasterResume(
        profile_id=profile_id,
        file_name="resume.txt",
        source_mime_type="text/plain",
        raw_text=raw_text,
        parsed_json={"sections": []},
    )
    db_session.add(resume)
    db_session.commit()
    return resume


def _create_job_requirement() -> dict:
    return JobRequirementPayload(
        role_summary="Senior backend engineer building APIs.",
        must_have_skills=["Python", "FastAPI", "PostgreSQL"],
        nice_to_have_skills=["Docker"],
        responsibilities=["Build APIs"],
        experience_requirements=["5+ years of experience"],
        education_requirements=[],
        work_authorization="Must be authorized to work in the United States.",
        location_requirement="Remote",
        seniority="Senior",
        red_flags=[],
    ).model_dump(mode="json")


def _create_job(db_session, profile_id: str, *, title: str, location: str = "Remote") -> Job:
    job = Job(
        profile_id=profile_id,
        source="greenhouse",
        source_job_id=title.lower().replace(" ", "-"),
        stable_hash=f"stable-{title.lower().replace(' ', '-')}",
        title=title,
        company="Acme",
        location=location,
        description=(
            "Python, FastAPI, PostgreSQL. 5+ years of experience. Remote in the United States."
        ),
        apply_url="https://careers.acme.example/jobs/1",
        status="discovered",
    )
    db_session.add(job)
    db_session.commit()
    return job


def test_job_scoring_persists_a_profile_specific_match(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    _create_resume(
        db_session,
        profile.id,
        "Backend engineer with 7 years of experience in Python, FastAPI, PostgreSQL, and Docker.",
    )
    job = _create_job(db_session, profile.id, title="Senior Backend Engineer")
    db_session.add(
        JobRequirement(
            profile_id=profile.id,
            job_id=job.id,
            structured_json=_create_job_requirement(),
            analyzed_by="qwen3",
        )
    )
    db_session.add(
        AnswerBank(
            profile_id=profile.id,
            key="work_authorization",
            question_text="Are you authorized to work in the United States?",
            answer_text="I am authorized to work in the United States without sponsorship.",
            category="work_authorization",
        )
    )
    db_session.commit()

    response = score_job_for_profile(db=db_session, profile_id=profile.id, job_id=job.id)

    assert response.profile_id == profile.id
    assert response.job_id == job.id
    assert response.decision == "pass"
    assert response.total_score >= 70
    assert response.skills_match == 100
    assert response.work_authorization_match == 100

    stored = db_session.query(JobMatch).filter(JobMatch.job_id == job.id).one()
    assert stored.profile_id == profile.id
    assert stored.decision == "pass"
    assert db_session.get(Job, job.id).status == "matched"


def test_job_scoring_hard_rejects_an_excluded_role(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=["data scientist"],
    )
    _create_resume(
        db_session,
        profile.id,
        "Backend engineer with 7 years of experience in Python, FastAPI, PostgreSQL, and Docker.",
    )
    job = _create_job(db_session, profile.id, title="Data Scientist")
    db_session.add(
        JobRequirement(
            profile_id=profile.id,
            job_id=job.id,
            structured_json=_create_job_requirement(),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()

    response = score_job_for_profile(db=db_session, profile_id=profile.id, job_id=job.id)

    assert response.decision == "reject"
    assert "Excluded role matched" in response.reject_reason


def test_job_scoring_rejects_cross_profile_jobs(db_session) -> None:
    profile_one = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    profile_two = _create_profile(
        db_session,
        target_roles=["product engineer"],
        locations=["Austin"],
        excluded_roles=[],
    )
    job = _create_job(db_session, profile_one.id, title="Senior Backend Engineer")
    db_session.add(
        JobRequirement(
            profile_id=profile_one.id,
            job_id=job.id,
            structured_json=_create_job_requirement(),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile_two.id}/jobs/{job.id}/score")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_score_new_jobs_endpoint_scores_only_analyzed_jobs(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    _create_resume(
        db_session,
        profile.id,
        "Backend engineer with 7 years of experience in Python, FastAPI, PostgreSQL, and Docker.",
    )
    analyzed_job = _create_job(db_session, profile.id, title="Senior Backend Engineer")
    _create_job(db_session, profile.id, title="Platform Engineer")
    db_session.add(
        JobRequirement(
            profile_id=profile.id,
            job_id=analyzed_job.id,
            structured_json=_create_job_requirement(),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/agent/score-new-jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == profile.id
    assert body["jobs_considered"] == 2
    assert body["jobs_scored"] == 1
    assert body["jobs_skipped"] == 1
    assert len(body["matches"]) == 1
    assert body["matches"][0]["job_id"] == analyzed_job.id
