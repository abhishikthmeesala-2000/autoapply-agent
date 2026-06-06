from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Job, JobRequirement, Profile, ResumeVersion
from app.job_analysis.schemas import JobRequirementPayload
from app.resume_tailoring.schemas import TailoredResumePayload

from .schemas import AtsValidationBreakdown, AtsValidationIssue, AtsValidationResponse


class AtsValidationError(RuntimeError):
    pass


class AtsValidationEligibilityError(AtsValidationError):
    pass


ALLOWED_SECTION_TYPES = {
    "summary",
    "skills",
    "experience",
    "projects",
    "education",
    "certifications",
}


@dataclass(frozen=True)
class ValidationMetrics:
    structure_score: float
    keyword_score: float
    readability_score: float
    extractability_score: float

    @property
    def total(self) -> float:
        return round(
            (
                self.structure_score * 0.35
                + self.keyword_score * 0.30
                + self.readability_score * 0.20
                + self.extractability_score * 0.15
            ),
            2,
        )


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _extract_years(text: str) -> Optional[float]:
    matches = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", text.lower())]
    if not matches:
        return None
    return max(matches)


def _contains_phrase(haystack: str, needle: str) -> bool:
    normalized_haystack = f" {_normalize_text(haystack)} "
    normalized_needle = _normalize_text(needle)
    if not normalized_needle:
        return False
    return f" {normalized_needle} " in normalized_haystack


def _fetch_profile(db: Session, profile_id: str) -> Profile:
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise LookupError("Profile not found.")
    return profile


def _fetch_job(db: Session, profile_id: str, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if job is None or job.profile_id != profile_id:
        raise LookupError("Job not found for this profile.")
    return job


def _fetch_resume_version(db: Session, profile_id: str, resume_version_id: str) -> ResumeVersion:
    resume_version = db.get(ResumeVersion, resume_version_id)
    if resume_version is None or resume_version.profile_id != profile_id:
        raise LookupError("Resume version not found for this profile.")
    return resume_version


def _fetch_requirement(db: Session, job_id: str) -> JobRequirementPayload:
    requirement = (
        db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
        .scalars()
        .first()
    )
    if requirement is None:
        raise AtsValidationEligibilityError("Job requirements must be analyzed before validation.")
    return JobRequirementPayload.model_validate(requirement.structured_json)


def _collect_requirement_phrases(requirement: JobRequirementPayload) -> list[str]:
    values: list[str] = []
    for value in [
        *requirement.must_have_skills,
        *requirement.nice_to_have_skills,
        *requirement.responsibilities,
        *requirement.experience_requirements,
        *requirement.education_requirements,
    ]:
        if value and value.strip():
            values.append(value.strip())
    return list(dict.fromkeys(values))


def _plain_text_resume(tailored: TailoredResumePayload) -> str:
    parts: list[str] = []
    for section in tailored.sections:
        parts.append(section.heading)
        for bullet in section.bullets:
            parts.append(bullet.text)
    return "\n".join(parts)


def _validate_structure(tailored: TailoredResumePayload) -> tuple[float, list[AtsValidationIssue]]:
    issues: list[AtsValidationIssue] = []
    score = 100.0

    if not tailored.sections:
        issues.append(
            AtsValidationIssue(
                code="no_sections",
                message="Tailored resume has no sections.",
                severity="high",
            )
        )
        return 0.0, issues

    seen_types: set[str] = set()
    for section in tailored.sections:
        if section.section_type not in ALLOWED_SECTION_TYPES:
            issues.append(
                AtsValidationIssue(
                    code="invalid_section_type",
                    message=f"Unsupported section type: {section.section_type}.",
                    severity="high",
                )
            )
            score -= 20

        if section.section_type in seen_types:
            issues.append(
                AtsValidationIssue(
                    code="duplicate_section",
                    message=f"Duplicate section type: {section.section_type}.",
                    severity="medium",
                )
            )
            score -= 10
        seen_types.add(section.section_type)

        if not section.heading.strip():
            issues.append(
                AtsValidationIssue(
                    code="empty_heading",
                    message="Section heading is empty.",
                    severity="high",
                )
            )
            score -= 10

        if not section.bullets:
            issues.append(
                AtsValidationIssue(
                    code="empty_section",
                    message=f"Section {section.section_type} has no bullets.",
                    severity="medium",
                )
            )
            score -= 5

        for bullet in section.bullets:
            if not bullet.text.strip():
                issues.append(
                    AtsValidationIssue(
                        code="empty_bullet",
                        message=f"Section {section.section_type} contains an empty bullet.",
                        severity="high",
                    )
                )
                score -= 12
            if len(bullet.text) > 240:
                issues.append(
                    AtsValidationIssue(
                        code="long_bullet",
                        message="A bullet exceeds the recommended ATS length.",
                        severity="medium",
                    )
                )
                score -= 6
            if not bullet.evidence_ids or not bullet.source_refs or not bullet.source_texts:
                issues.append(
                    AtsValidationIssue(
                        code="missing_traceability",
                        message="Every bullet must keep evidence references.",
                        severity="high",
                    )
                )
                score -= 15

    return max(0.0, round(score, 2)), issues


def _validate_keyword_coverage(
    *,
    tailored: TailoredResumePayload,
    requirement: JobRequirementPayload,
) -> tuple[float, list[AtsValidationIssue]]:
    issues: list[AtsValidationIssue] = []
    requirement_phrases = _collect_requirement_phrases(requirement)
    if not requirement_phrases:
        return 75.0, issues

    resume_text = _plain_text_resume(tailored)
    matched = 0
    for phrase in requirement_phrases:
        if _contains_phrase(resume_text, phrase):
            matched += 1

    coverage = (matched / len(requirement_phrases)) * 100.0
    if coverage < 50.0:
        issues.append(
            AtsValidationIssue(
                code="low_keyword_coverage",
                message="Resume covers too few job requirements.",
                severity="high",
            )
        )
    elif coverage < 75.0:
        issues.append(
            AtsValidationIssue(
                code="moderate_keyword_coverage",
                message="Resume covers some, but not most, job requirements.",
                severity="medium",
            )
        )

    return round(min(100.0, coverage), 2), issues


def _validate_readability(tailored: TailoredResumePayload) -> tuple[float, list[AtsValidationIssue]]:
    issues: list[AtsValidationIssue] = []
    bullet_lengths: list[int] = []
    section_count = len(tailored.sections)
    bullet_count = 0

    for section in tailored.sections:
        for bullet in section.bullets:
            bullet_count += 1
            bullet_lengths.append(len(bullet.text))
            if "\t" in bullet.text:
                issues.append(
                    AtsValidationIssue(
                        code="tab_character",
                        message="Tabs can hurt ATS readability.",
                        severity="medium",
                    )
                )
            if "\n" in bullet.text:
                issues.append(
                    AtsValidationIssue(
                        code="multiline_bullet",
                        message="Bullets should stay single-line for ATS extractability.",
                        severity="medium",
                    )
                )

    if not bullet_lengths:
        return 0.0, issues

    avg_length = mean(bullet_lengths)
    score = 100.0
    if avg_length > 180:
        score -= 20
    elif avg_length > 130:
        score -= 10

    if bullet_count < 4:
        score -= 10

    if section_count < 3:
        score -= 10

    if any(length > 240 for length in bullet_lengths):
        score -= 10

    return max(0.0, round(score, 2)), issues


def _validate_extractability(tailored: TailoredResumePayload) -> tuple[float, list[AtsValidationIssue]]:
    issues: list[AtsValidationIssue] = []
    resume_text = _plain_text_resume(tailored)
    score = 100.0

    if any(char in resume_text for char in ["|", "□", "■"]):
        issues.append(
            AtsValidationIssue(
                code="non_extractable_layout",
                message="Detected layout characters that can interfere with ATS extraction.",
                severity="medium",
            )
        )
        score -= 20

    if "\t" in resume_text:
        issues.append(
            AtsValidationIssue(
                code="tab_character",
                message="Tabs can make extraction inconsistent.",
                severity="medium",
            )
        )
        score -= 10

    if resume_text.count("\n") < 3:
        issues.append(
            AtsValidationIssue(
                code="too_sparse",
                message="Tailored resume is too sparse to validate cleanly.",
                severity="high",
            )
        )
        score -= 25

    return max(0.0, round(score, 2)), issues


def validate_resume_version_for_profile(
    *,
    db: Session,
    profile_id: str,
    resume_version_id: str,
) -> AtsValidationResponse:
    _fetch_profile(db, profile_id)
    resume_version = _fetch_resume_version(db, profile_id, resume_version_id)
    job = _fetch_job(db, profile_id, resume_version.job_id)
    requirement = _fetch_requirement(db, resume_version.job_id)

    tailored = TailoredResumePayload.model_validate(resume_version.tailored_json)
    if tailored.profile_id != profile_id or tailored.job_id != resume_version.job_id:
        raise AtsValidationEligibilityError("Tailored resume profile or job metadata is inconsistent.")

    structure_score, structure_issues = _validate_structure(tailored)
    keyword_score, keyword_issues = _validate_keyword_coverage(
        tailored=tailored,
        requirement=requirement,
    )
    readability_score, readability_issues = _validate_readability(tailored)
    extractability_score, extractability_issues = _validate_extractability(tailored)

    issues = structure_issues + keyword_issues + readability_issues + extractability_issues
    metrics = ValidationMetrics(
        structure_score=structure_score,
        keyword_score=keyword_score,
        readability_score=readability_score,
        extractability_score=extractability_score,
    )

    previous_ats_score = (
        float(resume_version.ats_score) if resume_version.ats_score is not None else None
    )
    resume_version.ats_score = metrics.total
    db.commit()
    db.refresh(resume_version)

    summary = (
        "Resume passes ATS validation."
        if metrics.total >= 70 and not any(issue.severity == "high" for issue in issues)
        else "Resume needs ATS improvements."
    )

    return AtsValidationResponse(
        profile_id=profile_id,
        job_id=job.id,
        resume_version_id=resume_version.id,
        valid=metrics.total >= 70 and not any(issue.severity == "high" for issue in issues),
        ats_score=metrics.total,
        breakdown=AtsValidationBreakdown(
            structure_score=structure_score,
            keyword_score=keyword_score,
            readability_score=readability_score,
            extractability_score=extractability_score,
        ),
        issues=issues,
        summary=summary,
        persisted=True,
        previous_ats_score=previous_ats_score,
    )
