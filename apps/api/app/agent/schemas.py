from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentRunMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jobs_discovered: int = 0
    jobs_scored: int = 0
    applications_prepared: int = 0
    applications_skipped: int = 0
    applications_today: int = 0
    max_applications_per_day: int = 0
    daily_limit_reached: bool = False
    approvals_required: int = 0
    notes: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class AgentControlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    agent_run_id: str
    run_type: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    summary: str
    metadata: AgentRunMetadata
    persisted: bool = True
