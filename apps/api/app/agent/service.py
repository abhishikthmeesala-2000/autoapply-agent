from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRun,
    Application,
    Profile,
    ProfileSetting,
    ResumeVersion,
)
from app.maintenance.service import record_audit_log
from app.job_scoring.schemas import JobMatchPayload
from app.job_discovery.service import discover_jobs_for_profile
from app.job_scoring.service import score_new_jobs_for_profile

from .schemas import AgentControlResponse, AgentRunMetadata


class AgentModeError(RuntimeError):
    pass


class AgentModeEligibilityError(AgentModeError):
    pass


def _fetch_profile(db: Session, profile_id: str) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")
    return profile


def _fetch_setting(db: Session, profile_id: str) -> ProfileSetting:
    setting = (
        db.execute(select(ProfileSetting).where(ProfileSetting.profile_id == profile_id))
        .scalars()
        .first()
    )
    if setting is None:
        raise LookupError("Profile settings not found.")
    if not setting.active:
        raise AgentModeEligibilityError("Profile automation is paused.")
    return setting


def _fetch_latest_run(db: Session, profile_id: str) -> Optional[AgentRun]:
    return (
        db.execute(
            select(AgentRun)
            .where(AgentRun.profile_id == profile_id, AgentRun.run_type == "continuous")
            .order_by(desc(AgentRun.created_at), desc(AgentRun.id))
            .limit(1)
        )
        .scalars()
        .first()
    )


def _load_metadata(agent_run: AgentRun) -> AgentRunMetadata:
    try:
        return AgentRunMetadata.model_validate(agent_run.metadata_json)
    except Exception:
        return AgentRunMetadata()


def _today_window() -> tuple[datetime, datetime]:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _applications_today(db: Session, profile_id: str) -> int:
    start, end = _today_window()
    return (
        db.execute(
            select(func.count(Application.id)).where(
                Application.profile_id == profile_id,
                Application.created_at >= start,
                Application.created_at < end,
            )
        )
        .scalar_one()
    )


def _latest_tailored_version_for_job(
    db: Session, profile_id: str, job_id: str
) -> Optional[ResumeVersion]:
    return (
        db.execute(
            select(ResumeVersion)
            .where(
                ResumeVersion.profile_id == profile_id,
                ResumeVersion.job_id == job_id,
            )
            .order_by(desc(ResumeVersion.version_number), desc(ResumeVersion.created_at))
            .limit(1)
        )
        .scalars()
        .first()
    )


def _existing_application(db: Session, profile_id: str, job_id: str) -> Optional[Application]:
    return (
        db.execute(
            select(Application).where(
                Application.profile_id == profile_id,
                Application.job_id == job_id,
            )
        )
        .scalars()
        .first()
    )


def _build_response(agent_run: AgentRun, metadata: AgentRunMetadata, summary: str) -> AgentControlResponse:
    return AgentControlResponse(
        profile_id=agent_run.profile_id,
        agent_run_id=agent_run.id,
        run_type=agent_run.run_type,
        status=agent_run.status,
        started_at=agent_run.started_at,
        ended_at=agent_run.ended_at,
        summary=summary,
        metadata=metadata,
        persisted=True,
    )


def _prepare_application_drafts(
    *,
    db: Session,
    profile_id: str,
    setting: ProfileSetting,
    scored_matches: list[JobMatchPayload],
    metadata: AgentRunMetadata,
) -> tuple[int, int, list[str]]:
    applications_today = _applications_today(db, profile_id)
    remaining_slots = max(setting.max_applications_per_day - applications_today, 0)
    metadata.applications_today = applications_today
    metadata.max_applications_per_day = setting.max_applications_per_day
    metadata.daily_limit_reached = remaining_slots <= 0

    prepared = 0
    skipped = 0
    notes: list[str] = []

    if remaining_slots <= 0:
        notes.append("Daily application limit reached.")
        metadata.notes.extend(notes)
        return prepared, skipped, notes

    pass_jobs = [job_match.job_id for job_match in scored_matches if job_match.decision == "pass"]
    for job_id in pass_jobs:
        if remaining_slots <= 0:
            metadata.daily_limit_reached = True
            notes.append("Stopped at the daily application limit.")
            break

        if _existing_application(db, profile_id, job_id) is not None:
            skipped += 1
            continue

        tailored_version = _latest_tailored_version_for_job(db, profile_id, job_id)
        if tailored_version is None:
            skipped += 1
            notes.append(f"Skipped job {job_id}: no tailored resume version found.")
            continue

        db.add(
            Application(
                profile_id=profile_id,
                job_id=job_id,
                resume_version_id=tailored_version.id,
                status="draft",
                approval_required=True,
            )
        )
        prepared += 1
        remaining_slots -= 1

    metadata.applications_prepared = prepared
    metadata.applications_skipped = skipped
    metadata.approvals_required = prepared
    metadata.notes.extend(notes)
    return prepared, skipped, notes


def _run_agent_cycle(
    *,
    db: Session,
    profile_id: str,
    setting: ProfileSetting,
    client: httpx.Client,
) -> AgentRunMetadata:
    metadata = AgentRunMetadata()

    discovery = discover_jobs_for_profile(db=db, profile_id=profile_id, client=client)
    metadata.jobs_discovered = discovery.jobs_found
    if discovery.blocked_sources:
        metadata.notes.append(
            "Blocked sources skipped: " + ", ".join(discovery.blocked_sources)
        )

    scoring = score_new_jobs_for_profile(db=db, profile_id=profile_id)
    metadata.jobs_scored = scoring.jobs_scored

    _prepare_application_drafts(
        db=db,
        profile_id=profile_id,
        setting=setting,
        scored_matches=scoring.matches,
        metadata=metadata,
    )

    if metadata.daily_limit_reached:
        metadata.notes.append("Application prep paused until tomorrow's limit resets.")

    return metadata


def _create_agent_run(db: Session, profile_id: str, metadata: AgentRunMetadata) -> AgentRun:
    agent_run = AgentRun(
        profile_id=profile_id,
        run_type="continuous",
        status="running",
        started_at=datetime.utcnow(),
        metadata_json=metadata.model_dump(mode="json"),
    )
    db.add(agent_run)
    db.flush()
    return agent_run


def _persist_run_status(
    db: Session,
    agent_run: AgentRun,
    *,
    status: str,
    metadata: AgentRunMetadata,
    ended_at: Optional[datetime] = None,
) -> None:
    agent_run.status = status
    agent_run.ended_at = ended_at
    agent_run.metadata_json = metadata.model_dump(mode="json")
    db.flush()


def start_continuous_agent_mode(
    *,
    db: Session,
    profile_id: str,
    client: httpx.Client,
) -> AgentControlResponse:
    _fetch_profile(db, profile_id)
    setting = _fetch_setting(db, profile_id)

    agent_run = _create_agent_run(db, profile_id, AgentRunMetadata())
    db.commit()
    db.refresh(agent_run)

    try:
        metadata = _run_agent_cycle(db=db, profile_id=profile_id, setting=setting, client=client)
        summary = (
            f"Discovered {metadata.jobs_discovered} jobs, scored {metadata.jobs_scored}, "
            f"prepared {metadata.applications_prepared} applications."
        )
        _persist_run_status(db, agent_run, status="running", metadata=metadata)
        record_audit_log(
            db=db,
            profile_id=profile_id,
            actor_type="user",
            action="agent_start",
            entity_type="agent_run",
            entity_id=agent_run.id,
            details_json=metadata.model_dump(mode="json"),
        )
        db.commit()
        db.refresh(agent_run)
        return _build_response(agent_run, metadata, summary)
    except Exception as exc:
        metadata = _load_metadata(agent_run)
        metadata.error = str(exc)
        metadata.notes.append("Agent cycle failed; automation remains paused for safety.")
        _persist_run_status(db, agent_run, status="paused", metadata=metadata)
        record_audit_log(
            db=db,
            profile_id=profile_id,
            actor_type="system",
            action="agent_start_failed",
            entity_type="agent_run",
            entity_id=agent_run.id,
            details_json=metadata.model_dump(mode="json"),
        )
        db.commit()
        db.refresh(agent_run)
        raise AgentModeError(f"Agent start failed: {exc}") from exc


def pause_continuous_agent_mode(*, db: Session, profile_id: str) -> AgentControlResponse:
    _fetch_profile(db, profile_id)
    agent_run = _fetch_latest_run(db, profile_id)
    if agent_run is None:
        raise LookupError("No agent run found for this profile.")

    metadata = _load_metadata(agent_run)
    metadata.notes.append("Continuous agent mode paused by the user.")
    _persist_run_status(db, agent_run, status="paused", metadata=metadata)
    record_audit_log(
        db=db,
        profile_id=profile_id,
        actor_type="user",
        action="agent_pause",
        entity_type="agent_run",
        entity_id=agent_run.id,
        details_json=metadata.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(agent_run)
    return _build_response(
        agent_run,
        metadata,
        "Continuous agent mode paused before final submission.",
    )


def stop_continuous_agent_mode(*, db: Session, profile_id: str) -> AgentControlResponse:
    _fetch_profile(db, profile_id)
    agent_run = _fetch_latest_run(db, profile_id)
    if agent_run is None:
        raise LookupError("No agent run found for this profile.")

    metadata = _load_metadata(agent_run)
    metadata.notes.append("Continuous agent mode stopped by the user.")
    _persist_run_status(db, agent_run, status="stopped", metadata=metadata, ended_at=datetime.utcnow())
    record_audit_log(
        db=db,
        profile_id=profile_id,
        actor_type="user",
        action="agent_stop",
        entity_type="agent_run",
        entity_id=agent_run.id,
        details_json=metadata.model_dump(mode="json"),
    )
    db.commit()
    db.refresh(agent_run)
    return _build_response(
        agent_run,
        metadata,
        "Continuous agent mode stopped and will not resume automatically.",
    )
