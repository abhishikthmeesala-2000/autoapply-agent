from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Job,
    JobMatch,
    JobRequirement,
    MasterResume,
    Profile,
    ResumeEvidence,
    ResumeSection,
    ResumeVersion,
)
from app.job_analysis.schemas import JobRequirementPayload

from .schemas import TailoredResumeBullet, TailoredResumePayload, TailoredResumeResponse, TailoredResumeSection


class ResumeTailoringError(RuntimeError):
    pass


class ResumeTailoringEligibilityError(ResumeTailoringError):
    pass


SECTION_PRIORITY = {
    "summary": 100,
    "skills": 90,
    "experience": 80,
    "projects": 70,
    "education": 50,
    "certifications": 40,
}

SECTION_CAPS = {
    "summary": 2,
    "skills": 4,
    "experience": 4,
    "projects": 3,
    "education": 2,
    "certifications": 2,
}


@dataclass(frozen=True)
class EvidenceCandidate:
    section_type: str
    heading: str
    evidence_id: str
    source_ref: str
    source_text: str
    score: int
    requirement_hits: tuple[str, ...]


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _tokenize(text: str) -> set[str]:
    return {token for token in _normalize_text(text).split() if token}


def _contains_phrase(haystack: str, needle: str) -> bool:
    normalized_haystack = f" {_normalize_text(haystack)} "
    normalized_needle = _normalize_text(needle)
    if not normalized_needle:
        return False
    return f" {normalized_needle} " in normalized_haystack


def _extract_years(text: str) -> Optional[float]:
    matches = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", text.lower())]
    if not matches:
        return None
    return max(matches)


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


def _fetch_job_match(db: Session, job_id: str) -> JobMatch:
    job_match = db.execute(select(JobMatch).where(JobMatch.job_id == job_id)).scalars().first()
    if job_match is None:
        raise ResumeTailoringEligibilityError("Job must be scored before tailoring.")
    if job_match.profile_id != job_match.job.profile_id:
        raise ResumeTailoringEligibilityError("Job match profile ownership is inconsistent.")
    if job_match.decision != "pass":
        raise ResumeTailoringEligibilityError("Only matched jobs can be tailored.")
    return job_match


def _fetch_latest_master_resume(db: Session, profile_id: str) -> MasterResume:
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
        raise ResumeTailoringEligibilityError("No master resume found for this profile.")
    return resume


def _fetch_resume_sections(db: Session, master_resume_id: str, profile_id: str) -> list[ResumeSection]:
    statement = (
        select(ResumeSection)
        .where(
            ResumeSection.master_resume_id == master_resume_id,
            ResumeSection.profile_id == profile_id,
        )
        .order_by(ResumeSection.created_at.asc(), ResumeSection.id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _fetch_resume_evidence(db: Session, master_resume_id: str, profile_id: str) -> list[ResumeEvidence]:
    statement = (
        select(ResumeEvidence)
        .where(
            ResumeEvidence.master_resume_id == master_resume_id,
            ResumeEvidence.profile_id == profile_id,
        )
        .order_by(ResumeEvidence.created_at.asc(), ResumeEvidence.id.asc())
    )
    return list(db.execute(statement).scalars().all())


def _fetch_requirement(db: Session, job_id: str) -> JobRequirementPayload:
    requirement = (
        db.execute(select(JobRequirement).where(JobRequirement.job_id == job_id))
        .scalars()
        .first()
    )
    if requirement is None:
        raise ResumeTailoringEligibilityError("Job requirements must be analyzed before tailoring.")
    return JobRequirementPayload.model_validate(requirement.structured_json)


def _collect_requirement_phrases(requirement: JobRequirementPayload) -> list[str]:
    phrases: list[str] = []
    for value in [
        requirement.role_summary,
        *requirement.must_have_skills,
        *requirement.nice_to_have_skills,
        *requirement.responsibilities,
        *requirement.experience_requirements,
        *requirement.education_requirements,
        requirement.work_authorization,
        requirement.location_requirement,
        requirement.seniority,
        *requirement.red_flags,
    ]:
        if value and value.strip():
            phrases.append(value.strip())
    return list(dict.fromkeys(phrases))


def _match_requirement_to_resume(requirement: str, resume_text: str) -> bool:
    normalized_requirement = requirement.lower().strip()
    if not normalized_requirement:
        return False

    if re.search(r"\d+(?:\.\d+)?\s*\+?\s*years?", normalized_requirement):
        requirement_years = _extract_years(normalized_requirement)
        resume_years = _extract_years(resume_text)
        if requirement_years is not None and resume_years is not None:
            return resume_years >= requirement_years

    if _contains_phrase(resume_text, requirement):
        return True

    requirement_tokens = _tokenize(requirement)
    if not requirement_tokens:
        return False

    resume_tokens = _tokenize(resume_text)
    overlap = requirement_tokens & resume_tokens
    return len(overlap) >= max(1, len(requirement_tokens) // 2)


def _score_evidence(
    *,
    section_type: str,
    source_text: str,
    requirement_phrases: list[str],
) -> tuple[int, tuple[str, ...]]:
    normalized_source = source_text.lower()
    hits: list[str] = []
    for phrase in requirement_phrases:
        if _contains_phrase(normalized_source, phrase):
            hits.append(phrase)

    score = SECTION_PRIORITY.get(section_type, 10) + len(hits) * 15

    source_tokens = _tokenize(source_text)
    if source_tokens:
        phrase_tokens = set().union(*(_tokenize(phrase) for phrase in requirement_phrases if phrase))
        score += min(len(source_tokens & phrase_tokens), 10) * 2

    return score, tuple(dict.fromkeys(hits))


def _build_candidates(
    *,
    sections: list[ResumeSection],
    evidence_items: list[ResumeEvidence],
    requirement_phrases: list[str],
) -> list[EvidenceCandidate]:
    section_by_id = {section.id: section for section in sections}
    candidates: list[EvidenceCandidate] = []

    for evidence in evidence_items:
        section = section_by_id.get(evidence.resume_section_id) if evidence.resume_section_id else None
        section_type = (section.section_type if section else "summary").lower()
        heading = section.heading if section else "Summary"
        score, hits = _score_evidence(
            section_type=section_type,
            source_text=evidence.claim_text,
            requirement_phrases=requirement_phrases,
        )
        candidates.append(
            EvidenceCandidate(
                section_type=section_type,
                heading=heading,
                evidence_id=evidence.id,
                source_ref=evidence.source_ref,
                source_text=evidence.claim_text,
                score=score,
                requirement_hits=hits,
            )
        )

    return candidates


def _select_candidates(candidates: list[EvidenceCandidate]) -> dict[str, list[EvidenceCandidate]]:
    selected: dict[str, list[EvidenceCandidate]] = defaultdict(list)
    grouped: dict[str, list[EvidenceCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.section_type].append(candidate)

    for section_type, items in grouped.items():
        items_sorted = sorted(
            items,
            key=lambda item: (-item.score, item.heading.lower(), item.source_ref, item.evidence_id),
        )
        cap = SECTION_CAPS.get(section_type, 2)
        positive = [item for item in items_sorted if item.score > 0]
        selected_items = positive[:cap] if positive else items_sorted[: min(cap, len(items_sorted))]
        selected[section_type] = selected_items

    return selected


def _build_sections(selected: dict[str, list[EvidenceCandidate]]) -> list[TailoredResumeSection]:
    section_order = ["summary", "skills", "experience", "projects", "education", "certifications"]
    sections: list[TailoredResumeSection] = []

    for section_type in section_order:
        items = selected.get(section_type)
        if not items:
            continue

        heading = items[0].heading if items[0].heading else section_type.title()
        bullets = [
            TailoredResumeBullet(
                text=item.source_text,
                evidence_ids=[item.evidence_id],
                source_refs=[item.source_ref],
                source_texts=[item.source_text],
            )
            for item in items
        ]
        sections.append(
            TailoredResumeSection(
                section_type=section_type,
                heading=heading,
                bullets=bullets,
            )
        )

    return sections


def _resolve_requirement_matches(
    *,
    requirement: JobRequirementPayload,
    resume_text: str,
) -> tuple[list[str], list[str]]:
    requirement_phrases = _collect_requirement_phrases(requirement)
    matched: list[str] = []
    unmet: list[str] = []

    for phrase in requirement_phrases:
        if _match_requirement_to_resume(phrase, resume_text):
            matched.append(phrase)
        else:
            unmet.append(phrase)

    return matched, unmet


def _next_version_number(db: Session, profile_id: str, job_id: str) -> int:
    highest = db.execute(
        select(func.max(ResumeVersion.version_number)).where(
            ResumeVersion.profile_id == profile_id,
            ResumeVersion.job_id == job_id,
        )
    ).scalar_one()
    return int(highest or 0) + 1


def tailor_resume_for_profile(
    *,
    db: Session,
    profile_id: str,
    job_id: str,
) -> TailoredResumeResponse:
    _fetch_profile(db, profile_id)
    job = _fetch_job(db, profile_id, job_id)
    job_match = _fetch_job_match(db, job_id)
    requirement = _fetch_requirement(db, job_id)
    master_resume = _fetch_latest_master_resume(db, profile_id)
    sections = _fetch_resume_sections(db, master_resume.id, profile_id)
    evidence_items = _fetch_resume_evidence(db, master_resume.id, profile_id)

    if not evidence_items:
        raise ResumeTailoringEligibilityError(
            "No resume evidence is available for this profile."
        )

    resume_text = "\n".join([master_resume.raw_text, *[item.claim_text for item in evidence_items]])
    matched_requirements, unmet_requirements = _resolve_requirement_matches(
        requirement=requirement,
        resume_text=resume_text,
    )

    requirement_phrases = _collect_requirement_phrases(requirement)
    candidates = _build_candidates(
        sections=sections,
        evidence_items=evidence_items,
        requirement_phrases=requirement_phrases,
    )
    selected = _select_candidates(candidates)
    tailored_sections = _build_sections(selected)
    selected_evidence_ids = [item.evidence_id for items in selected.values() for item in items]

    if not tailored_sections:
        raise ResumeTailoringEligibilityError(
            "Unable to build a tailored resume from the available evidence."
        )

    version_number = _next_version_number(db, profile_id, job_id)
    file_name = f"{job.title} - tailored resume v{version_number}.json"
    tailored_payload = TailoredResumePayload(
        profile_id=profile_id,
        job_id=job_id,
        job_match_id=job_match.id,
        master_resume_id=master_resume.id,
        version_number=version_number,
        generated_by="rule-based-evidence-tailoring",
        matched_requirements=matched_requirements,
        unmet_requirements=unmet_requirements,
        selected_evidence_ids=selected_evidence_ids,
        sections=tailored_sections,
    )

    resume_version = ResumeVersion(
        profile_id=profile_id,
        job_id=job_id,
        master_resume_id=master_resume.id,
        version_number=version_number,
        file_name=file_name,
        tailored_json=tailored_payload.model_dump(mode="json"),
        ats_score=None,
    )
    db.add(resume_version)
    db.flush()
    db.commit()
    db.refresh(resume_version)

    return TailoredResumeResponse(
        profile_id=profile_id,
        job_id=job_id,
        resume_version_id=resume_version.id,
        master_resume_id=master_resume.id,
        job_match_id=job_match.id,
        version_number=version_number,
        file_name=file_name,
        tailored_json=tailored_payload,
        ats_score=float(resume_version.ats_score) if resume_version.ats_score is not None else None,
    )
