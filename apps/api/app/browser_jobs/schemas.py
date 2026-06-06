from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, HttpUrl


class BrowserJobPayload(BaseModel):
    profile_id: str
    source: str
    title: str
    company: str
    location: Optional[str] = None
    description: str
    apply_url: HttpUrl
    page_url: HttpUrl


class BrowserJobResponse(BaseModel):
    profile_id: str
    title: str
    company: str
    source: str
    status: str = "received"
