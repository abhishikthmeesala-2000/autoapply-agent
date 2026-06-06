from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AnswerBank,
    Job,
    JobMatch,
    JobRequirement,
    MasterResume,
    Profile,
    ProfileSetting,
    ResumeEvidence,
)
from app.job_analysis.schemas import JobRequirementPayload

from .schemas import JobMatchPayload, ScoreNewJobsResponse

WORK_AUTH_KEYS = {
    "work_authorization",
    "work_authorization_status",
    "visa_status",
}


class JobScoringError(RuntimeError):
    pass


@dataclass(frozen=True)
class MatchComputation:
    total_score: float
    skills_match: int
    experience_match: int
    role_match: int
    location_match: int
    work_authorization_match: int
    decision: str
    reject_reason: Optional[str]


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _contains_phrase(haystack: str, needle: str) -> bool:
    normalized_haystack = f" {_normalize_text(haystack)} "
    normalized_needle = _normalize_text(needle)
    if not normalized_needle:
        return False
    return f" {normalized_needle} " in normalized_haystack


def _token_set(text: str) -> set[str]:
    return {token for token in _normalize_text(text).split() if token}


def _extract_years(text: str) -> Optional[float]:
    matches = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", text.lower())]
    if not matches:
        return None
    return max(matches)


def _fetch_setting(db: Session, profile_id: str) -> ProfileSetting:
    setting = (
        db.execute(select(ProfileSetting).where(ProfileSetting.profile_id == profile_id))
        .scalars()
        .first()
    )
    if setting is None:
        raise LookupError("Profile settings not found.")
    return setting


def _fetch_latest_resume_text(db: Session, profile_id: str) -> str:
    resume = (
        db.execute(
            select(MasterResume)
            .where(MasterResume.profile_id == profile_id)
            .order_by(desc(MasterResume.created_at), desc(MasterResume.id))
            .limit(1)
        )
        .scalars()
        .first()
    )
    if resume is None:
        return ""

    evidence_texts = db.execute(
        select(ResumeEvidence.claim_text)
        .where(ResumeEvidence.profile_id == profile_id, ResumeEvidence.master_resume_id == resume.id)
        .order_by(ResumeEvidence.created_at.asc(), ResumeEvidence.id.asc())
    ).all()

    return "\n".join([resume.raw_text] + [row[0] for row in evidence_texts if row[0]])


def _fetch_work_authorization_answer(db: Session, profile_id: str) -> Optional[str]:
    answer = (
        db.execute(
            select(AnswerBank.answer_text).where(
                AnswerBank.profile_id == profile_id,
                AnswerBank.key.in_(WORK_AUTH_KEYS),
            )
        )
        .scalars()
        .first()
    )
    if answer is None:
        return None
    return answer.strip()


def _requires_work_authorization(requirement: JobRequirementPayload) -> bool:
    haystack = " ".join(
        [
            requirement.work_authorization or "",
            requirement.location_requirement or "",
            requirement.role_summary,
            " ".join(requirement.red_flags),
        ]
    ).lower()
    trigger_phrases = [
        "authorized to work",
        "work authorization",
        "visa sponsorship",
        "sponsorship required",
        "must be authorized",
        "citizens only",
        "us citizen",
        "u.s. citizen",
        "without sponsorship",
    ]
    return any(phrase in haystack for phrase in trigger_phrases)


def _work_authorization_status(answer_text: Optional[str]) -> Optional[str]:
    if answer_text is None:
        return None

    normalized = _normalize_text(answer_text)
    negative_markers = [
        "not authorized",
        "need sponsorship",
        "requires sponsorship",
        "require sponsorship",
        "visa sponsorship",
        "will require sponsorship",
    ]
    positive_markers = [
        "authorized",
        "no sponsorship",
        "without sponsorship",
        "citizen",
    ]

    if any(marker in normalized for marker in negative_markers):
        return "negative"
    if any(marker in normalized for marker in positive_markers):
        return "positive"
    return "unknown"


def _score_skills(
    *,
    requirement: JobRequirementPayload,
    resume_text: str,
) -> int:
    skills = list(dict.fromkeys(requirement.must_have_skills + requirement.nice_to_have_skills))
    if not skills:
        return 70
    if not resume_text.strip():
        return 50

    resume_norm = _normalize_text(resume_text)
    must_have = requirement.must_have_skills
    nice_to_have = requirement.nice_to_have_skills

    if must_have:
        must_matched = sum(1 for skill in must_have if _contains_phrase(resume_norm, skill))
        nice_matched = sum(1 for skill in nice_to_have if _contains_phrase(resume_norm, skill))
        must_ratio = must_matched / len(must_have)
        nice_ratio = (
            nice_matched / len(nice_to_have) if nice_to_have else 0.75
        )
        return int(round((must_ratio * 80.0) + (nice_ratio * 20.0)))

    nice_matched = sum(1 for skill in nice_to_have if _contains_phrase(resume_norm, skill))
    return int(round((nice_matched / len(nice_to_have)) * 100)) if nice_to_have else 70


def _score_role(
    *,
    setting: ProfileSetting,
    job: Job,
    requirement: JobRequirementPayload,
) -> int:
    target_roles = [role for role in setting.target_roles if role and role.strip()]
    if not target_roles:
        return 70

    title_norm = _normalize_text(" ".join([job.title, requirement.role_summary]))
    title_tokens = _token_set(" ".join([job.title, requirement.role_summary]))

    best_score = 0.0
    for role in target_roles:
        role_norm = _normalize_text(role)
        if not role_norm:
            continue
        if role_norm in title_norm:
            return 100
        role_tokens = _token_set(role)
        if not role_tokens:
            continue
        overlap = len(role_tokens & title_tokens) / len(role_tokens)
        best_score = max(best_score, overlap)

    return int(round(best_score * 100))


def _score_location(
    *,
    setting: ProfileSetting,
    job: Job,
    requirement: JobRequirementPayload,
) -> tuple[int, Optional[str]]:
    locations = [location for location in setting.locations if location and location.strip()]
    if not locations:
        return 70, None

    job_location = " ".join(
        part for part in [job.location or "", requirement.location_requirement or ""] if part
    ).strip()
    if not job_location:
        return 60, None

    location_norm = _normalize_text(job_location)
    if "remote" in location_norm:
        if any("remote" in _normalize_text(location) for location in locations):
            return 100, None
        return 80, None

    for location in locations:
        if _contains_phrase(job_location, location):
            return 100, None

    return 0, "Location mismatch."


def _score_experience(*, requirement: JobRequirementPayload, resume_text: str) -> int:
    required_years = max(
        [value for value in [_extract_years(text) for text in requirement.experience_requirements] if value is not None],
        default=None,
    )
    resume_years = _extract_years(resume_text)

    if required_years is not None and resume_years is not None:
        ratio = min(resume_years / required_years, 1.0)
        return int(round(ratio * 100))

    if required_years is not None:
        return 40 if not resume_text.strip() else 70

    if resume_years is not None:
        return 75

    return 70 if resume_text.strip() else 50


def _score_work_authorization(
    *,
    requirement: JobRequirementPayload,
    work_authorization_answer: Optional[str],
) -> tuple[int, Optional[str]]:
    if not _requires_work_authorization(requirement):
        return 70, None

    status = _work_authorization_status(work_authorization_answer)
    if status == "positive":
        return 100, None
    if status == "negative":
        return 0, "Work authorization mismatch."
    return 60, None


def _compute_match(
    *,
    setting: ProfileSetting,
    job: Job,
    requirement: JobRequirementPayload,
    resume_text: str,
    work_authorization_answer: Optional[str],
) -> MatchComputation:
    skills_match = _score_skills(requirement=requirement, resume_text=resume_text)
    experience_match = _score_experience(requirement=requirement, resume_text=resume_text)
    role_match = _score_role(setting=setting, job=job, requirement=requirement)
    location_match, location_reject_reason = _score_location(
        setting=setting, job=job, requirement=requirement
    )
    work_authorization_match, work_auth_reject_reason = _score_work_authorization(
        requirement=requirement, work_authorization_answer=work_authorization_answer
    )

    weighted_total = (
        (skills_match * 0.35)
        + (experience_match * 0.20)
        + (role_match * 0.20)
        + (location_match * 0.15)
        + (work_authorization_match * 0.10)
    )
    total_score = round(weighted_total, 2)

    reject_reason: Optional[str] = None
    excluded_roles = [
        role.strip() for role in setting.excluded_roles if role and role.strip()
    ]
    for excluded_role in excluded_roles:
        if _contains_phrase(job.title, excluded_role) or _contains_phrase(
            requirement.role_summary, excluded_role
        ) or _contains_phrase(job.description, excluded_role):
            reject_reason = f"Excluded role matched: {excluded_role}."
            break

    if reject_reason is None and location_reject_reason is not None:
        reject_reason = location_reject_reason

    if reject_reason is None and work_auth_reject_reason is not None:
        reject_reason = work_auth_reject_reason

    if reject_reason is None and total_score < setting.match_threshold:
        reject_reason = (
            f"Below match threshold ({total_score:.2f} < {setting.match_threshold})."
        )

    decision = "pass" if reject_reason is None else "reject"

    return MatchComputation(
        total_score=total_score,
        skills_match=skills_match,
        experience_match=experience_match,
        role_match=role_match,
        location_match=location_match,
        work_authorization_match=work_authorization_match,
        decision=decision,
        reject_reason=reject_reason,
    )


def _upsert_job_match(
    *,
    db: Session,
    profile_id: str,
    job: Job,
    match: MatchComputation,
) -> JobMatch:
    existing = (
        db.execute(select(JobMatch).where(JobMatch.job_id == job.id)).scalars().first()
    )
    if existing is None:
        existing = JobMatch(
            profile_id=profile_id,
            job_id=job.id,
            total_score=match.total_score,
            skills_match=match.skills_match,
            experience_match=match.experience_match,
            role_match=match.role_match,
            location_match=match.location_match,
            work_authorization_match=match.work_authorization_match,
            decision=match.decision,
            reject_reason=match.reject_reason,
        )
        db.add(existing)
    else:
        existing.profile_id = profile_id
        existing.total_score = match.total_score
        existing.skills_match = match.skills_match
        existing.experience_match = match.experience_match
        existing.role_match = match.role_match
        existing.location_match = match.location_match
        existing.work_authorization_match = match.work_authorization_match
        existing.decision = match.decision
        existing.reject_reason = match.reject_reason

    job.status = "matched" if match.decision == "pass" else "rejected"
    db.flush()
    return existing


def _build_match_payload(
    *,
    job_match: JobMatch,
    match: MatchComputation,
    threshold: int,
    job_status: str,
) -> JobMatchPayload:
    return JobMatchPayload(
        profile_id=job_match.profile_id,
        job_id=job_match.job_id,
        job_match_id=job_match.id,
        match_threshold=threshold,
        total_score=float(match.total_score),
        skills_match=match.skills_match,
        experience_match=match.experience_match,
        role_match=match.role_match,
        location_match=match.location_match,
        work_authorization_match=match.work_authorization_match,
        decision=match.decision,
        reject_reason=match.reject_reason,
        job_status=job_status,
    )


def score_job_for_profile(
    *,
    db: Session,
    profile_id: str,
    job_id: str,
) -> JobMatchPayload:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")

    job = db.get(Job, job_id)
    if job is None or job.profile_id != profile_id:
        raise LookupError("Job not found for this profile.")

    setting = _fetch_setting(db, profile_id)
    requirement = (
        db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
        .scalars()
        .first()
    )
    if requirement is None:
        raise LookupError("Job requirements not found. Analyze the job first.")

    structured_requirement = JobRequirementPayload.model_validate(requirement.structured_json)
    resume_text = _fetch_latest_resume_text(db, profile_id)
    work_authorization_answer = _fetch_work_authorization_answer(db, profile_id)

    try:
        match = _compute_match(
            setting=setting,
            job=job,
            requirement=structured_requirement,
            resume_text=resume_text,
            work_authorization_answer=work_authorization_answer,
        )
    except Exception as exc:
        raise JobScoringError(f"Job scoring failed: {exc}") from exc

    job_match = _upsert_job_match(db=db, profile_id=profile_id, job=job, match=match)
    db.commit()
    db.refresh(job_match)

    return _build_match_payload(
        job_match=job_match,
        match=match,
        threshold=setting.match_threshold,
        job_status=job.status,
    )


def score_new_jobs_for_profile(
    *,
    db: Session,
    profile_id: str,
) -> ScoreNewJobsResponse:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")

    setting = _fetch_setting(db, profile_id)
    resume_text = _fetch_latest_resume_text(db, profile_id)
    work_authorization_answer = _fetch_work_authorization_answer(db, profile_id)

    jobs = list(
        db.execute(
            select(Job)
            .where(Job.profile_id == profile_id, Job.status == "discovered")
            .order_by(Job.created_at.asc(), Job.id.asc())
        )
        .scalars()
        .all()
    )

    matches: list[JobMatchPayload] = []
    skipped = 0

    try:
        for job in jobs:
            requirement = (
                db.execute(select(JobRequirement).where(JobRequirement.job_id == job.id))
                .scalars()
                .first()
            )
            if requirement is None:
                skipped += 1
                continue

            structured_requirement = JobRequirementPayload.model_validate(requirement.structured_json)
            match = _compute_match(
                setting=setting,
                job=job,
                requirement=structured_requirement,
                resume_text=resume_text,
                work_authorization_answer=work_authorization_answer,
            )
            job_match = _upsert_job_match(db=db, profile_id=profile_id, job=job, match=match)
            matches.append(
                _build_match_payload(
                    job_match=job_match,
                    match=match,
                    threshold=setting.match_threshold,
                    job_status=job.status,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    passed = sum(1 for item in matches if item.decision == "pass")
    rejected = sum(1 for item in matches if item.decision == "reject")

    return ScoreNewJobsResponse(
        profile_id=profile_id,
        jobs_considered=len(jobs),
        jobs_scored=len(matches),
        jobs_skipped=skipped,
        jobs_passed=passed,
        jobs_rejected=rejected,
        matches=matches,
    )
