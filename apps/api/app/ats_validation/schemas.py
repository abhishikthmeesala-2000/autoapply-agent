from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AtsValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    severity: str


class AtsValidationBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structure_score: float
    keyword_score: float
    readability_score: float
    extractability_score: float


class AtsValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    job_id: str
    resume_version_id: str
    valid: bool
    ats_score: float
    breakdown: AtsValidationBreakdown
    issues: list[AtsValidationIssue] = Field(default_factory=list)
    summary: str
    persisted: bool = True
    previous_ats_score: Optional[float] = None

