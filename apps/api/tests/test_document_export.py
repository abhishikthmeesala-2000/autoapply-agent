from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.db.models import Job, MasterResume, Profile, ProfileSetting, ResumeVersion, User
from app.main import app, get_db_session
from app.resume_tailoring.schemas import TailoredResumeBullet, TailoredResumePayload, TailoredResumeSection


def _create_profile(db_session, *, name: str = "Export Profile") -> Profile:
    user = User(email=f"export-{uuid4().hex}@example.com")
    db_session.add(user)
    db_session.flush()

    profile = Profile(user_id=user.id, name=name, location="Remote")
    db_session.add(profile)
    db_session.flush()

    db_session.add(
        ProfileSetting(
            profile_id=profile.id,
            target_roles=["backend engineer"],
            locations=["Remote"],
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
        source_job_id="export-job",
        stable_hash=f"stable-{uuid4().hex}",
        title="Senior Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build Python APIs with FastAPI.",
        apply_url="https://careers.acme.example/jobs/1",
        status="discovered",
    )
    db_session.add(job)
    db_session.flush()
    return job


def _create_master_resume(db_session, profile_id: str) -> MasterResume:
    resume = MasterResume(
        profile_id=profile_id,
        file_name="master-resume.docx",
        source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        raw_text="Backend engineer with Python and FastAPI experience.",
        parsed_json={"sections": []},
    )
    db_session.add(resume)
    db_session.commit()
    return resume


def _create_resume_version(db_session, profile_id: str, job_id: str) -> ResumeVersion:
    master_resume = _create_master_resume(db_session, profile_id)
    payload = TailoredResumePayload(
        profile_id=profile_id,
        job_id=job_id,
        job_match_id=str(uuid4()),
        master_resume_id=master_resume.id,
        version_number=1,
        generated_by="rule-based-evidence-tailoring",
        matched_requirements=["Python", "FastAPI"],
        unmet_requirements=[],
        selected_evidence_ids=["evidence-1"],
        sections=[
            TailoredResumeSection(
                section_type="summary",
                heading="Summary",
                bullets=[
                    TailoredResumeBullet(
                        text="Backend engineer with Python and FastAPI experience.",
                        evidence_ids=["evidence-1"],
                        source_refs=["summary:1:1"],
                        source_texts=["Backend engineer with Python and FastAPI experience."],
                    )
                ],
            ),
            TailoredResumeSection(
                section_type="skills",
                heading="Skills",
                bullets=[
                    TailoredResumeBullet(
                        text="Python",
                        evidence_ids=["evidence-2"],
                        source_refs=["skills:2:1"],
                        source_texts=["Python"],
                    )
                ],
            ),
        ],
    )
    resume_version = ResumeVersion(
        profile_id=profile_id,
        job_id=job_id,
        master_resume_id=master_resume.id,
        version_number=1,
        file_name="tailored.json",
        tailored_json=payload.model_dump(mode="json"),
        ats_score=87.5,
    )
    db_session.add(resume_version)
    db_session.commit()
    return resume_version


def test_resume_export_returns_zip_with_docx_and_pdf(db_session) -> None:
    profile = _create_profile(db_session)
    job = _create_job(db_session, profile.id)
    resume_version = _create_resume_version(db_session, profile.id, job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile.id}/resume_versions/{resume_version.id}/export"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].endswith('tailored.zip"')
    assert response.headers["x-docx-file-name"] == "tailored.docx"
    assert response.headers["x-pdf-file-name"] == "tailored.pdf"

    archive = ZipFile(BytesIO(response.content))
    assert sorted(archive.namelist()) == ["tailored.docx", "tailored.pdf"]

    docx_bytes = archive.read("tailored.docx")
    pdf_bytes = archive.read("tailored.pdf")

    docx = Document(BytesIO(docx_bytes))
    docx_text = "\n".join(paragraph.text for paragraph in docx.paragraphs)
    assert "SUMMARY" in docx_text
    assert "Backend engineer with Python and FastAPI experience." in docx_text

    pdf_reader = PdfReader(BytesIO(pdf_bytes))
    pdf_text = "\n".join((page.extract_text() or "") for page in pdf_reader.pages)
    assert "SUMMARY" in pdf_text
    assert "Python" in pdf_text


def test_resume_export_rejects_cross_profile_access(db_session) -> None:
    profile_one = _create_profile(db_session, name="Export One")
    profile_two = _create_profile(db_session, name="Export Two")
    job = _create_job(db_session, profile_one.id)
    resume_version = _create_resume_version(db_session, profile_one.id, job.id)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile_two.id}/resume_versions/{resume_version.id}/export"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
