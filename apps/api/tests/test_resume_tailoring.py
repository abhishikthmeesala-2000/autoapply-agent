from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import (
    Job,
    JobMatch,
    JobRequirement,
    MasterResume,
    Profile,
    ProfileSetting,
    ResumeEvidence,
    ResumeSection,
    ResumeVersion,
    User,
)
from app.job_analysis.schemas import JobRequirementPayload
from app.main import app, get_db_session


def _create_profile(
    db_session,
    *,
    target_roles: list[str],
    locations: list[str],
    excluded_roles: list[str],
) -> Profile:
    user = User(email=f"tailoring-{uuid4().hex}@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name="Tailor", location="Remote")
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=target_roles,
            locations=locations,
            excluded_roles=excluded_roles,
            job_sources=["https://jobs.example.com"],
            match_threshold=70,
            max_applications_per_day=5,
        )
    )
    db_session.commit()
    return profile


def _create_resume_with_evidence(db_session, profile_id: str) -> MasterResume:
    master_resume = MasterResume(
        profile_id=profile_id,
        file_name="master-resume.docx",
        source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        raw_text=(
            "SUMMARY\n"
            "Backend engineer with 7 years of experience.\n"
            "SKILLS\n"
            "Python\n"
            "FastAPI\n"
            "PostgreSQL\n"
            "EXPERIENCE\n"
            "Built APIs and internal automation tools.\n"
            "PROJECTS\n"
            "Job automation platform for local workflows.\n"
            "EDUCATION\n"
            "B.S. Computer Science, State University, 2018\n"
            "CERTIFICATIONS\n"
            "AWS Certified Developer Associate"
        ),
        parsed_json={"sections": []},
    )
    db_session.add(master_resume)
    db_session.flush()

    sections = [
        ("summary", "Summary", ["Backend engineer with 7 years of experience."]),
        ("skills", "Skills", ["Python", "FastAPI", "PostgreSQL"]),
        ("experience", "Experience", ["Built APIs and internal automation tools."]),
        ("projects", "Projects", ["Job automation platform for local workflows."]),
        ("education", "Education", ["B.S. Computer Science, State University, 2018"]),
        ("certifications", "Certifications", ["AWS Certified Developer Associate"]),
    ]

    for index, (section_type, heading, claims) in enumerate(sections, start=1):
        section = ResumeSection(
            profile_id=profile_id,
            master_resume_id=master_resume.id,
            section_type=section_type,
            heading=heading,
            content_json={"section_type": section_type, "heading": heading, "items": claims},
        )
        db_session.add(section)
        db_session.flush()

        for claim_index, claim in enumerate(claims, start=1):
            db_session.add(
                ResumeEvidence(
                    profile_id=profile_id,
                    master_resume_id=master_resume.id,
                    resume_section_id=section.id,
                    evidence_key=f"{section_type}:{index}:{claim_index}",
                    source_text=claim,
                    claim_text=claim,
                    source_ref=f"{section_type}:{index}:{claim_index}",
                )
            )
            db_session.flush()

    db_session.commit()
    return master_resume


def _create_job(db_session, profile_id: str, *, title: str = "Senior Backend Engineer") -> Job:
    job = Job(
        profile_id=profile_id,
        source="greenhouse",
        source_job_id=title.lower().replace(" ", "-"),
        stable_hash=f"stable-{title.lower().replace(' ', '-')}",
        title=title,
        company="Acme",
        location="Remote",
        description=(
            "Build Python APIs. Required: 5+ years experience, FastAPI, PostgreSQL. "
            "Preferred: AWS, Docker. Remote in the United States."
        ),
        apply_url="https://careers.acme.example/jobs/101",
        status="discovered",
    )
    db_session.add(job)
    db_session.commit()
    return job


def _create_job_requirement(
    db_session,
    *,
    profile_id: str,
    job_id: str,
    must_have_skills: list[str],
    nice_to_have_skills: list[str] | None = None,
) -> None:
    payload = JobRequirementPayload(
        role_summary="Backend engineer building Python APIs.",
        must_have_skills=must_have_skills,
        nice_to_have_skills=nice_to_have_skills or ["AWS"],
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
            structured_json=payload.model_dump(mode="json"),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()


def _create_pass_match(db_session, *, profile_id: str, job_id: str, decision: str = "pass") -> None:
    db_session.add(
        JobMatch(
            profile_id=profile_id,
            job_id=job_id,
            total_score=88.0,
            skills_match=95,
            experience_match=90,
            role_match=100,
            location_match=100,
            work_authorization_match=100,
            decision=decision,
            reject_reason=None if decision == "pass" else "Below threshold.",
        )
    )
    db_session.commit()


def test_tailor_resume_persists_evidence_backed_version(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    _create_resume_with_evidence(db_session, profile.id)
    job = _create_job(db_session, profile.id)
    _create_job_requirement(
        db_session,
        profile_id=profile.id,
        job_id=job.id,
        must_have_skills=["Python", "FastAPI", "PostgreSQL"],
    )
    _create_pass_match(db_session, profile_id=profile.id, job_id=job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/jobs/{job.id}/tailor-resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "tailored"
    assert body["version_number"] == 1
    assert body["tailored_json"]["profile_id"] == profile.id
    assert body["tailored_json"]["job_id"] == job.id
    assert body["tailored_json"]["selected_evidence_ids"]
    assert all(
        bullet["evidence_ids"]
        for section in body["tailored_json"]["sections"]
        for bullet in section["bullets"]
    )

    stored = db_session.query(ResumeVersion).filter(ResumeVersion.job_id == job.id).one()
    assert stored.profile_id == profile.id
    assert stored.version_number == 1
    assert stored.tailored_json["generated_by"] == "rule-based-evidence-tailoring"


def test_tailor_resume_records_unmet_requirements_instead_of_inventing_claims(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    _create_resume_with_evidence(db_session, profile.id)
    job = _create_job(db_session, profile.id)
    _create_job_requirement(
        db_session,
        profile_id=profile.id,
        job_id=job.id,
        must_have_skills=["Python", "FastAPI", "Go"],
    )
    _create_pass_match(db_session, profile_id=profile.id, job_id=job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/jobs/{job.id}/tailor-resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "Go" in body["tailored_json"]["unmet_requirements"]
    assert all(
        "Go" not in bullet["text"]
        for section in body["tailored_json"]["sections"]
        for bullet in section["bullets"]
    )


def test_tailor_resume_rejects_jobs_from_other_profiles(db_session) -> None:
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
    _create_resume_with_evidence(db_session, profile_one.id)
    job = _create_job(db_session, profile_one.id)
    _create_job_requirement(
        db_session,
        profile_id=profile_one.id,
        job_id=job.id,
        must_have_skills=["Python"],
    )
    _create_pass_match(db_session, profile_id=profile_one.id, job_id=job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile_two.id}/jobs/{job.id}/tailor-resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_tailor_resume_requires_a_passed_match(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
        excluded_roles=[],
    )
    _create_resume_with_evidence(db_session, profile.id)
    job = _create_job(db_session, profile.id)
    _create_job_requirement(
        db_session,
        profile_id=profile.id,
        job_id=job.id,
        must_have_skills=["Python"],
    )
    _create_pass_match(db_session, profile_id=profile.id, job_id=job.id, decision="reject")

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(f"/profiles/{profile.id}/jobs/{job.id}/tailor-resume")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
