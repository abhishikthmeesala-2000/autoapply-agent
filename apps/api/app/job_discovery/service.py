from __future__ import annotations

from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job, Profile, ProfileSetting

from .connectors import (
    AshbyConnector,
    BaseJobConnector,
    GenericCareerPageConnector,
    GreenhouseConnector,
    JobDiscoveryBlockedError,
    LeverConnector,
)
from .schemas import JobDiscoveryResult


def _normalize_source(source_url: str) -> str:
    lowered = source_url.lower()
    if "greenhouse" in lowered:
        return "greenhouse"
    if "lever" in lowered:
        return "lever"
    if "ashby" in lowered:
        return "ashby"
    return "generic"


def _create_connector(source_url: str) -> BaseJobConnector:
    source = _normalize_source(source_url)
    if source == "greenhouse":
        return GreenhouseConnector()
    if source == "lever":
        return LeverConnector()
    if source == "ashby":
        return AshbyConnector()
    return GenericCareerPageConnector()


def _fetch_setting(db: Session, profile_id: str) -> ProfileSetting:
    setting = (
        db.execute(select(ProfileSetting).where(ProfileSetting.profile_id == profile_id))
        .scalars()
        .first()
    )
    if setting is None:
        raise LookupError("Profile settings not found.")
    return setting


def _existing_hashes(db: Session, profile_id: str) -> set[str]:
    rows = db.execute(select(Job.stable_hash).where(Job.profile_id == profile_id)).all()
    return {row[0] for row in rows}


def discover_jobs_for_profile(
    *,
    db: Session,
    profile_id: str,
    client: Optional[httpx.Client] = None,
    connectors: Optional[dict[str, BaseJobConnector]] = None,
) -> JobDiscoveryResult:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")

    setting = _fetch_setting(db, profile_id)
    sources = [source.strip() for source in setting.job_sources if source and source.strip()]
    result = JobDiscoveryResult(profile_id=profile_id, sources_processed=len(sources))
    if not sources:
        return result

    http_client = client or httpx.Client(timeout=30.0)
    connector_map = connectors or {}
    seen_hashes = _existing_hashes(db, profile_id)
    inserted = 0
    deduped = 0
    pending_jobs: list[Job] = []

    try:
        for source_url in sources:
            connector = connector_map.get(source_url) or _create_connector(source_url)
            try:
                discovered = connector.discover(
                    source_url=source_url,
                    target_roles=setting.target_roles,
                    client=http_client,
                )
            except JobDiscoveryBlockedError:
                result.blocked_sources.append(source_url)
                continue
            except Exception:
                continue

            for job in discovered:
                result.jobs_found += 1
                if job.stable_hash in seen_hashes:
                    deduped += 1
                    continue

                pending_jobs.append(
                    Job(
                        profile_id=profile_id,
                        source=job.source,
                        source_job_id=job.source_job_id,
                        stable_hash=job.stable_hash,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        description=job.description,
                        apply_url=job.apply_url,
                        status="discovered",
                    )
                )
                seen_hashes.add(job.stable_hash)
                inserted += 1

        if pending_jobs:
            db.add_all(pending_jobs)
            db.commit()

        result.jobs_inserted = inserted
        result.jobs_deduped = deduped
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        if client is None:
            http_client.close()
