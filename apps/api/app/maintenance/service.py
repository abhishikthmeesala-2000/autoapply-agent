from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    AnswerBank,
    Application,
    ApplicationAnswer,
    AuditLog,
    Job,
    JobMatch,
    JobRequirement,
    MasterResume,
    Profile,
    ProfileSetting,
    ResumeEvidence,
    ResumeSection,
    ResumeVersion,
)

from .schemas import DeletionResponse


class MaintenanceError(RuntimeError):
    pass


class MaintenanceEligibilityError(MaintenanceError):
    pass


_BACKUP_ITERATIONS = 390_000


def _fetch_profile(db: Session, profile_id: str) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")
    return profile


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _serialize_row(row: Any) -> dict[str, Any]:
    columns = row.__table__.columns.keys()
    payload: dict[str, Any] = {}
    for column in columns:
        payload[column] = _normalize_scalar(getattr(row, column))
    return payload


def _serialize_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [_serialize_row(row) for row in rows]


def record_audit_log(
    *,
    db: Session,
    profile_id: str,
    actor_type: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details_json: dict[str, Any] | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        profile_id=profile_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details_json or {},
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def list_audit_logs_for_profile(db: Session, profile_id: str) -> list[AuditLog]:
    _fetch_profile(db, profile_id)
    return list(
        db.execute(
            select(AuditLog)
            .where(AuditLog.profile_id == profile_id)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
        )
        .scalars()
        .all()
    )


def _profile_backup_payload(db: Session, profile_id: str) -> dict[str, Any]:
    profile = _fetch_profile(db, profile_id)
    setting = (
        db.execute(select(ProfileSetting).where(ProfileSetting.profile_id == profile_id))
        .scalars()
        .first()
    )

    master_resumes = list(
        db.execute(
            select(MasterResume)
            .where(MasterResume.profile_id == profile_id)
            .order_by(MasterResume.created_at.asc(), MasterResume.id.asc())
        )
        .scalars()
        .all()
    )

    sections = list(
        db.execute(
            select(ResumeSection)
            .where(ResumeSection.profile_id == profile_id)
            .order_by(ResumeSection.created_at.asc(), ResumeSection.id.asc())
        )
        .scalars()
        .all()
    )
    evidence_items = list(
        db.execute(
            select(ResumeEvidence)
            .where(ResumeEvidence.profile_id == profile_id)
            .order_by(ResumeEvidence.created_at.asc(), ResumeEvidence.id.asc())
        )
        .scalars()
        .all()
    )
    jobs = list(
        db.execute(
            select(Job).where(Job.profile_id == profile_id).order_by(Job.created_at.asc(), Job.id.asc())
        )
        .scalars()
        .all()
    )
    job_requirements = list(
        db.execute(
            select(JobRequirement)
            .where(JobRequirement.profile_id == profile_id)
            .order_by(JobRequirement.created_at.asc(), JobRequirement.id.asc())
        )
        .scalars()
        .all()
    )
    job_matches = list(
        db.execute(
            select(JobMatch).where(JobMatch.profile_id == profile_id).order_by(JobMatch.created_at.asc(), JobMatch.id.asc())
        )
        .scalars()
        .all()
    )
    resume_versions = list(
        db.execute(
            select(ResumeVersion)
            .where(ResumeVersion.profile_id == profile_id)
            .order_by(ResumeVersion.created_at.asc(), ResumeVersion.id.asc())
        )
        .scalars()
        .all()
    )
    applications = list(
        db.execute(
            select(Application)
            .where(Application.profile_id == profile_id)
            .order_by(Application.created_at.asc(), Application.id.asc())
        )
        .scalars()
        .all()
    )
    answers = list(
        db.execute(
            select(ApplicationAnswer)
            .where(ApplicationAnswer.profile_id == profile_id)
            .order_by(ApplicationAnswer.created_at.asc(), ApplicationAnswer.id.asc())
        )
        .scalars()
        .all()
    )
    answer_bank = list(
        db.execute(
            select(AnswerBank)
            .where(AnswerBank.profile_id == profile_id)
            .order_by(AnswerBank.created_at.asc(), AnswerBank.id.asc())
        )
        .scalars()
        .all()
    )
    agent_runs = list(
        db.execute(
            select(AgentRun)
            .where(AgentRun.profile_id == profile_id)
            .order_by(AgentRun.created_at.asc(), AgentRun.id.asc())
        )
        .scalars()
        .all()
    )
    audit_logs = list_audit_logs_for_profile(db, profile_id)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "profile": _serialize_row(profile),
        "profile_setting": _serialize_row(setting) if setting else None,
        "master_resumes": _serialize_rows(master_resumes),
        "resume_sections": _serialize_rows(sections),
        "resume_evidence": _serialize_rows(evidence_items),
        "jobs": _serialize_rows(jobs),
        "job_requirements": _serialize_rows(job_requirements),
        "job_matches": _serialize_rows(job_matches),
        "resume_versions": _serialize_rows(resume_versions),
        "applications": _serialize_rows(applications),
        "application_answers": _serialize_rows(answers),
        "answer_bank": _serialize_rows(answer_bank),
        "agent_runs": _serialize_rows(agent_runs),
        "audit_logs": _serialize_rows(audit_logs),
        "counts": {
            "master_resumes": len(master_resumes),
            "resume_sections": len(sections),
            "resume_evidence": len(evidence_items),
            "jobs": len(jobs),
            "job_requirements": len(job_requirements),
            "job_matches": len(job_matches),
            "resume_versions": len(resume_versions),
            "applications": len(applications),
            "application_answers": len(answers),
            "answer_bank": len(answer_bank),
            "agent_runs": len(agent_runs),
            "audit_logs": len(audit_logs),
        },
    }


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_BACKUP_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def create_encrypted_profile_backup(
    *,
    db: Session,
    profile_id: str,
    confirm_profile_name: str,
    passphrase: str,
) -> tuple[str, bytes]:
    profile = _fetch_profile(db, profile_id)
    if profile.name.strip().lower() != confirm_profile_name.strip().lower():
        raise MaintenanceEligibilityError("Profile name confirmation did not match.")

    payload = _profile_backup_payload(db, profile_id)
    envelope = {
        "version": 1,
        "profile_id": profile_id,
        "backup": payload,
    }
    salt = os.urandom(16)
    key = _derive_fernet_key(passphrase, salt)
    token = Fernet(key).encrypt(json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    backup_document = {
        "format": "careeros-encrypted-backup",
        "profile_id": profile_id,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iterations": _BACKUP_ITERATIONS,
        "ciphertext": base64.b64encode(token).decode("ascii"),
    }
    file_name = f"careeros-profile-{profile_id}-backup.json.enc"
    return file_name, json.dumps(backup_document, separators=(",", ":"), sort_keys=True).encode("utf-8")


def decrypt_encrypted_profile_backup(data: bytes, passphrase: str) -> dict[str, Any]:
    document = json.loads(data.decode("utf-8"))
    salt = base64.b64decode(document["salt"])
    ciphertext = base64.b64decode(document["ciphertext"])
    key = _derive_fernet_key(passphrase, salt)
    payload = json.loads(Fernet(key).decrypt(ciphertext).decode("utf-8"))
    return payload


def delete_profile_data(
    *,
    db: Session,
    profile_id: str,
    confirm_profile_name: str,
) -> DeletionResponse:
    profile = _fetch_profile(db, profile_id)
    if profile.name.strip().lower() != confirm_profile_name.strip().lower():
        raise MaintenanceEligibilityError("Profile name confirmation did not match.")

    counts: dict[str, int] = {}
    delete_order = [
        (ApplicationAnswer, ApplicationAnswer.profile_id),
        (Application, Application.profile_id),
        (AnswerBank, AnswerBank.profile_id),
        (ResumeVersion, ResumeVersion.profile_id),
        (JobMatch, JobMatch.profile_id),
        (JobRequirement, JobRequirement.profile_id),
        (ResumeEvidence, ResumeEvidence.profile_id),
        (ResumeSection, ResumeSection.profile_id),
        (MasterResume, MasterResume.profile_id),
        (Job, Job.profile_id),
        (AgentRun, AgentRun.profile_id),
        (ProfileSetting, ProfileSetting.profile_id),
    ]

    try:
        for model, column in delete_order:
            rows = db.execute(select(model).where(column == profile_id)).scalars().all()
            counts[model.__tablename__] = len(rows)
            db.execute(delete(model).where(column == profile_id))

        record_audit_log(
            db=db,
            profile_id=profile_id,
            actor_type="user",
            action="delete_profile_data",
            entity_type="profile",
            entity_id=profile_id,
            details_json={"deleted_counts": counts, "profile_name": profile.name},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    preserved_audit_logs = len(list_audit_logs_for_profile(db, profile_id))
    return DeletionResponse(
        profile_id=profile_id,
        preserved_audit_logs=preserved_audit_logs,
        deleted_counts=counts,
    )
