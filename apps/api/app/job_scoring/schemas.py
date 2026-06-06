from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobMatchPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    job_id: str
    job_match_id: str
    match_threshold: int
    total_score: float
    skills_match: int
    experience_match: int
    role_match: int
    location_match: int
    work_authorization_match: int
    decision: str
    reject_reason: Optional[str] = None
    job_status: str


class ScoreNewJobsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    jobs_considered: int
    jobs_scored: int
    jobs_skipped: int
    jobs_passed: int
    jobs_rejected: int
    matches: list[JobMatchPayload]

