from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.models import AnswerBank, Job, MasterResume, Profile, ProfileSetting, User
from app.main import app, get_db_session
from app.maintenance.service import decrypt_encrypted_profile_backup, record_audit_log


def _create_profile(db_session, *, name: str = "Maintenance") -> Profile:
    user = User(email=f"maintenance-{uuid4().hex}@example.com")
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


def _seed_profile_data(db_session, profile: Profile) -> None:
    master_resume = MasterResume(
        profile_id=profile.id,
        file_name="resume.docx",
        source_mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        raw_text="Backend engineer with Python and FastAPI experience.",
        parsed_json={"sections": []},
    )
    db_session.add(master_resume)

    job = Job(
        profile_id=profile.id,
        source="greenhouse",
        source_job_id="1",
        stable_hash=f"stable-{uuid4().hex}",
        title="Senior Backend Engineer",
        company="Acme",
        location="Remote",
        description="Build APIs.",
        apply_url="https://careers.acme.example/jobs/1",
        status="discovered",
    )
    db_session.add(job)
    db_session.add(
        AnswerBank(
            profile_id=profile.id,
            key="work_authorization",
            question_text="Authorized to work?",
            answer_text="Yes",
            category="work_authorization",
        )
    )
    db_session.flush()
    record_audit_log(
        db=db_session,
        profile_id=profile.id,
        actor_type="user",
        action="seed_profile_data",
        entity_type="profile",
        entity_id=profile.id,
        details_json={"resume_id": master_resume.id, "job_id": job.id},
    )
    db_session.commit()


def test_encrypted_backup_round_trip_includes_audit_logs(db_session) -> None:
    profile = _create_profile(db_session)
    _seed_profile_data(db_session, profile)

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/profiles/{profile.id}/backup",
                json={
                    "passphrase": "correct horse battery staple",
                    "confirm_profile_name": profile.name,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-backup-encrypted"] == "true"
    assert response.headers["content-disposition"].endswith(".json.enc\"")

    payload = decrypt_encrypted_profile_backup(response.content, "correct horse battery staple")
    assert payload["profile_id"] == profile.id
    assert payload["backup"]["profile"]["name"] == profile.name
    assert payload["backup"]["counts"]["master_resumes"] == 1
    assert payload["backup"]["counts"]["audit_logs"] == 1


def test_delete_profile_data_preserves_audit_logs_and_requires_confirmation(db_session) -> None:
    profile = _create_profile(db_session)
    _seed_profile_data(db_session, profile)
    setting_id = profile.setting.id
    record_audit_log(
        db=db_session,
        profile_id=profile.id,
        actor_type="user",
        action="pre_delete",
        entity_type="profile",
        entity_id=profile.id,
        details_json={"note": "keep this log"},
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            rejected = client.request(
                "DELETE",
                f"/profiles/{profile.id}/data",
                json={"confirm_profile_name": "Wrong Name"},
            )
            response = client.request(
                "DELETE",
                f"/profiles/{profile.id}/data",
                json={"confirm_profile_name": profile.name},
            )
    finally:
        app.dependency_overrides.clear()

    assert rejected.status_code == 400
    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == profile.id
    assert body["preserved_audit_logs"] == 3
    assert body["deleted_counts"]["jobs"] == 1
    assert body["deleted_counts"]["master_resumes"] == 1
    assert db_session.get(ProfileSetting, setting_id) is None
    assert db_session.query(Job).filter(Job.profile_id == profile.id).count() == 0
    assert db_session.query(MasterResume).filter(MasterResume.profile_id == profile.id).count() == 0
    assert db_session.query(AnswerBank).filter(AnswerBank.profile_id == profile.id).count() == 0
    assert db_session.query(Profile).filter(Profile.id == profile.id).count() == 1


def test_audit_log_endpoint_returns_newest_first(db_session) -> None:
    profile = _create_profile(db_session)
    record_audit_log(
        db=db_session,
        profile_id=profile.id,
        actor_type="user",
        action="first_action",
        entity_type="profile",
        entity_id=profile.id,
        details_json={},
    )
    record_audit_log(
        db=db_session,
        profile_id=profile.id,
        actor_type="user",
        action="second_action",
        entity_type="profile",
        entity_id=profile.id,
        details_json={},
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        with TestClient(app) as client:
            response = client.get(f"/profiles/{profile.id}/audit-logs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert [entry["action"] for entry in body[:2]] == ["second_action", "first_action"]
