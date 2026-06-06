from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResumeItem(BaseModel):
    text: str
    evidence_id: str


class ResumeSectionPayload(BaseModel):
    section_type: str
    heading: str
    items: list[ResumeItem] = Field(default_factory=list)


class MasterResumePayload(BaseModel):
    id: str
    profile_id: str
    file_name: str
    source_mime_type: str
    raw_text: str
    parsed_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ResumeEvidencePayload(BaseModel):
    id: str
    profile_id: str
    master_resume_id: str
    resume_section_id: Optional[str]
    evidence_key: str
    source_text: str
    claim_text: str
    source_ref: str
    created_at: datetime
    updated_at: datetime


class ResumeUploadResponse(BaseModel):
    master_resume_id: str
    status: str = "parsed"
    sections: int
    evidence_count: int
