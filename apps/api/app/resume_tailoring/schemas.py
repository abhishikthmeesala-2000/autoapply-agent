from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TailoredResumeBullet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    source_texts: list[str] = Field(default_factory=list)


class TailoredResumeSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: str
    heading: str
    bullets: list[TailoredResumeBullet] = Field(default_factory=list)


class TailoredResumePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    job_id: str
    job_match_id: str
    master_resume_id: str
    version_number: int
    generated_by: str
    matched_requirements: list[str] = Field(default_factory=list)
    unmet_requirements: list[str] = Field(default_factory=list)
    selected_evidence_ids: list[str] = Field(default_factory=list)
    sections: list[TailoredResumeSection] = Field(default_factory=list)


class TailoredResumeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    job_id: str
    resume_version_id: str
    master_resume_id: str
    job_match_id: str
    version_number: int
    file_name: str
    status: str = "tailored"
    tailored_json: TailoredResumePayload
    ats_score: Optional[float] = None

