from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DiscoveredJob(BaseModel):
    source: str
    source_job_id: Optional[str] = None
    stable_hash: str
    title: str
    company: str
    location: Optional[str] = None
    description: str
    apply_url: Optional[str] = None


class JobDiscoveryResult(BaseModel):
    profile_id: str
    sources_processed: int = 0
    jobs_found: int = 0
    jobs_inserted: int = 0
    jobs_deduped: int = 0
    blocked_sources: list[str] = Field(default_factory=list)
