from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import (
    Job,
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
from app.resume_tailoring.schemas import TailoredResumeBullet, TailoredResumePayload, TailoredResumeSection
from app.main import app, get_db_session


def _create_profile(db_session, *, target_roles: list[str], locations: list[str]) -> Profile:
    user = User(email=f"ats-{uuid4().hex}@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name="ATS", location="Remote")
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=target_roles,
            locations=locations,
            excluded_roles=[],
            job_sources=["https://jobs.example.com"],
            match_threshold=70,
            max_applications_per_day=5,
        )
    )
    db_session.commit()
    return profile


def _create_job(db_session, profile_id: str) -> Job:
    job = Job(
        profile_id=profile_id,
        source="greenhouse",
        source_job_id="job-1",
        stable_hash=f"stable-{uuid4().hex}",
        title="Senior Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build Python APIs with 5+ years of experience and FastAPI.",
        apply_url="https://careers.acme.example/jobs/1",
        status="discovered",
    )
    db_session.add(job)
    db_session.commit()
    return job


def _create_requirement(db_session, profile_id: str, job_id: str) -> None:
    payload = JobRequirementPayload(
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
            structured_json=payload.model_dump(mode="json"),
            analyzed_by="qwen3",
        )
    )
    db_session.commit()


def _create_master_resume_with_evidence(db_session, profile_id: str) -> MasterResume:
    resume = MasterResume(
        profile_id=profile_id,
        file_name="resume.docx",
        source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        raw_text=(
            "SUMMARY\nBackend engineer with 7 years of experience.\n"
            "SKILLS\nPython\nFastAPI\nDocker\n"
            "EXPERIENCE\nBuilt APIs with Python and FastAPI.\n"
            "PROJECTS\nBuilt job automation tooling.\n"
            "EDUCATION\nB.S. Computer Science\n"
            "CERTIFICATIONS\nAWS Certified Developer Associate"
        ),
        parsed_json={"sections": []},
    )
    db_session.add(resume)
    db_session.flush()

    sections = [
        ("summary", "Summary", ["Backend engineer with 7 years of experience."]),
        ("skills", "Skills", ["Python", "FastAPI", "Docker"]),
        ("experience", "Experience", ["Built APIs with Python and FastAPI."]),
        ("projects", "Projects", ["Built job automation tooling."]),
        ("education", "Education", ["B.S. Computer Science"]),
        ("certifications", "Certifications", ["AWS Certified Developer Associate"]),
    ]

    for index, (section_type, heading, claims) in enumerate(sections, start=1):
        section = ResumeSection(
            profile_id=profile_id,
            master_resume_id=resume.id,
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
                    master_resume_id=resume.id,
                    resume_section_id=section.id,
                    evidence_key=f"{section_type}:{index}:{claim_index}",
                    source_text=claim,
                    claim_text=claim,
                    source_ref=f"{section_type}:{index}:{claim_index}",
                )
            )
            db_session.flush()

    db_session.commit()
    return resume


def _create_tailored_resume_version(db_session, profile_id: str, job_id: str) -> ResumeVersion:
    resume = _create_master_resume_with_evidence(db_session, profile_id)
    payload = TailoredResumePayload(
        profile_id=profile_id,
        job_id=job_id,
        job_match_id=str(uuid4()),
        master_resume_id=resume.id,
        version_number=1,
        generated_by="rule-based-evidence-tailoring",
        matched_requirements=["Python", "FastAPI", "5+ years of experience"],
        unmet_requirements=["Docker"],
        selected_evidence_ids=["e1", "e2", "e3"],
        sections=[
            TailoredResumeSection(
                section_type="summary",
                heading="Summary",
                bullets=[
                    TailoredResumeBullet(
                        text=(
                            "Backend engineer with 7 years of experience and 5+ years of experience "
                            "in Python and FastAPI."
                        ),
                        evidence_ids=["e1"],
                        source_refs=["summary:1:1"],
                        source_texts=[
                            "Backend engineer with 7 years of experience and 5+ years of experience in Python and FastAPI."
                        ],
                    )
                ],
            ),
            TailoredResumeSection(
                section_type="skills",
                heading="Skills",
                bullets=[
                    TailoredResumeBullet(
                        text="Python",
                        evidence_ids=["e2"],
                        source_refs=["skills:2:1"],
                        source_texts=["Python"],
                    ),
                    TailoredResumeBullet(
                        text="FastAPI",
                        evidence_ids=["e3"],
                        source_refs=["skills:2:2"],
                        source_texts=["FastAPI"],
                    ),
                ],
            ),
            TailoredResumeSection(
                section_type="experience",
                heading="Experience",
                bullets=[
                    TailoredResumeBullet(
                        text="Built APIs with Python and FastAPI.",
                        evidence_ids=["e4"],
                        source_refs=["experience:3:1"],
                        source_texts=["Built APIs with Python and FastAPI."],
                    )
                ],
            ),
        ],
    )
    resume_version = ResumeVersion(
        profile_id=profile_id,
        job_id=job_id,
        master_resume_id=resume.id,
        version_number=1,
        file_name="tailored.json",
        tailored_json=payload.model_dump(mode="json"),
        ats_score=None,
    )
    db_session.add(resume_version)
    db_session.commit()
    return resume_version


def test_ats_validation_persists_score_for_clean_template(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
    )
    job = _create_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)
    resume_version = _create_tailored_resume_version(db_session, profile.id, job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile.id}/resume_versions/{resume_version.id}/validate"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == profile.id
    assert body["resume_version_id"] == resume_version.id
    assert body["valid"] is True
    assert body["ats_score"] >= 70
    assert body["breakdown"]["structure_score"] >= 80
    assert body["breakdown"]["extractability_score"] >= 80

    stored = db_session.get(ResumeVersion, resume_version.id)
    assert stored.ats_score is not None


def test_ats_validation_rejects_bad_layout_and_low_coverage(db_session) -> None:
    profile = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
    )
    job = _create_job(db_session, profile.id)
    _create_requirement(db_session, profile.id, job.id)

    resume = _create_master_resume_with_evidence(db_session, profile.id)
    bad_payload = TailoredResumePayload(
        profile_id=profile.id,
        job_id=job.id,
        job_match_id=str(uuid4()),
        master_resume_id=resume.id,
        version_number=1,
        generated_by="rule-based-evidence-tailoring",
        matched_requirements=[],
        unmet_requirements=["Python", "FastAPI", "Docker"],
        selected_evidence_ids=["e1"],
        sections=[
            TailoredResumeSection(
                section_type="summary",
                heading="Summary",
                bullets=[
                    TailoredResumeBullet(
                        text="| table | like | layout | breaks ATS |",
                        evidence_ids=["e1"],
                        source_refs=["summary:1:1"],
                        source_texts=["Backend engineer with 7 years of experience."],
                    )
                ],
            )
        ],
    )
    resume_version = ResumeVersion(
        profile_id=profile.id,
        job_id=job.id,
        master_resume_id=resume.id,
        version_number=1,
        file_name="tailored.json",
        tailored_json=bad_payload.model_dump(mode="json"),
        ats_score=None,
    )
    db_session.add(resume_version)
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile.id}/resume_versions/{resume_version.id}/validate"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["ats_score"] < 70
    assert any(issue["code"] == "low_keyword_coverage" for issue in body["issues"])
    assert any(issue["code"] == "non_extractable_layout" for issue in body["issues"])


def test_ats_validation_rejects_cross_profile_resume_version(db_session) -> None:
    profile_one = _create_profile(
        db_session,
        target_roles=["backend engineer"],
        locations=["Remote"],
    )
    profile_two = _create_profile(
        db_session,
        target_roles=["product engineer"],
        locations=["Austin"],
    )
    job = _create_job(db_session, profile_one.id)
    _create_requirement(db_session, profile_one.id, job.id)
    resume_version = _create_tailored_resume_version(db_session, profile_one.id, job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile_two.id}/resume_versions/{resume_version.id}/validate"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
