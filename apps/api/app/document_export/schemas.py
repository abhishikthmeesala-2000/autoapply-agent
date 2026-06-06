from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResumeExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    resume_version_id: str
    archive_name: str
    docx_name: str
    pdf_name: str
    status: str = "exported"

