from __future__ import annotations

from hashlib import sha256

from sqlalchemy.orm import Session

from app.db.models import Job, Profile

from .schemas import BrowserJobPayload, BrowserJobResponse


def _stable_hash(payload: BrowserJobPayload) -> str:
    raw = "|".join(
        [
            payload.source,
            payload.title,
            payload.company,
            payload.location or "",
            str(payload.apply_url),
        ]
    )
    return sha256(raw.lower().encode("utf-8")).hexdigest()


def receive_browser_job(*, db: Session, payload: BrowserJobPayload) -> BrowserJobResponse:
    profile = db.get(Profile, payload.profile_id)
    if profile is None:
        raise LookupError("Profile not found.")

    stable_hash = _stable_hash(payload)
    existing = (
        db.query(Job)
        .filter(Job.profile_id == payload.profile_id, Job.stable_hash == stable_hash)
        .one_or_none()
    )
    if existing is None:
        db.add(
            Job(
                profile_id=payload.profile_id,
                source=payload.source,
                source_job_id=None,
                stable_hash=stable_hash,
                title=payload.title,
                company=payload.company,
                location=payload.location,
                description=payload.description,
                apply_url=str(payload.apply_url),
                status="discovered",
            )
        )
        db.commit()

    return BrowserJobResponse(
        profile_id=payload.profile_id,
        title=payload.title,
        company=payload.company,
        source=payload.source,
    )
