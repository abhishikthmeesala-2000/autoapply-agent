from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import MasterResume, Profile, ResumeEvidence, ResumeSection

from .parser import extract_text_from_upload, parse_resume_text
from .schemas import ResumeUploadResponse
from .vector_store import ResumeVectorStore


@dataclass
class ResumeIngestionResult:
    master_resume: MasterResume
    sections: list[ResumeSection]
    evidence: list[ResumeEvidence]


def ingest_resume_upload(
    *,
    db: Session,
    profile_id: str,
    file_name: str,
    mime_type: str,
    file_bytes: bytes,
    vector_store: ResumeVectorStore,
) -> ResumeUploadResponse:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")

    raw_text = extract_text_from_upload(file_name=file_name, mime_type=mime_type, data=file_bytes)
    parsed = parse_resume_text(raw_text)

    master_resume = MasterResume(
        profile_id=profile_id,
        file_name=file_name,
        source_mime_type=mime_type,
        raw_text=parsed.raw_text,
        parsed_json={
            "sections": [section.model_dump() for section in parsed.sections],
        },
    )
    db.add(master_resume)
    db.flush()

    sections: list[ResumeSection] = []
    evidence_records: list[ResumeEvidence] = []
    vector_payload: list[tuple[str, str, str]] = []

    for section in parsed.sections:
        db_section = ResumeSection(
            profile_id=profile_id,
            master_resume_id=master_resume.id,
            section_type=section.section_type,
            heading=section.heading,
            content_json=section.model_dump(),
        )
        db.add(db_section)
        db.flush()
        sections.append(db_section)

        for item in section.items:
            evidence = ResumeEvidence(
                profile_id=profile_id,
                master_resume_id=master_resume.id,
                resume_section_id=db_section.id,
                evidence_key=item.evidence_id,
                source_text=item.text,
                claim_text=item.text,
                source_ref=item.evidence_id,
            )
            db.add(evidence)
            db.flush()
            evidence_records.append(evidence)
            vector_payload.append((evidence.id, item.text, item.evidence_id))

    db.commit()

    vector_store.upsert_resume_evidence(
        profile_id=profile_id,
        master_resume_id=master_resume.id,
        evidence=vector_payload,
    )

    return ResumeUploadResponse(
        master_resume_id=master_resume.id,
        sections=len(sections),
        evidence_count=len(evidence_records),
    )


def get_latest_master_resume(db: Session, profile_id: str) -> MasterResume | None:
    statement = (
        select(MasterResume)
        .where(MasterResume.profile_id == profile_id)
        .order_by(desc(MasterResume.created_at), desc(MasterResume.id))
        .limit(1)
    )
    return db.execute(statement).scalars().first()


def list_resume_evidence(db: Session, profile_id: str) -> list[ResumeEvidence]:
    statement = (
        select(ResumeEvidence)
        .where(ResumeEvidence.profile_id == profile_id)
        .order_by(ResumeEvidence.created_at.asc(), ResumeEvidence.id.asc())
    )
    return list(db.execute(statement).scalars().all())
