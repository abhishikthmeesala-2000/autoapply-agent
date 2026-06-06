from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator


def _clean_string_list(values: list[StrictStr]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        stripped = value.strip()
        if not stripped:
            raise ValueError("List items must not be empty.")
        cleaned.append(stripped)
    return cleaned


class JobRequirementPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_summary: StrictStr = Field(min_length=1)
    must_have_skills: list[StrictStr] = Field(default_factory=list)
    nice_to_have_skills: list[StrictStr] = Field(default_factory=list)
    responsibilities: list[StrictStr] = Field(default_factory=list)
    experience_requirements: list[StrictStr] = Field(default_factory=list)
    education_requirements: list[StrictStr] = Field(default_factory=list)
    work_authorization: Optional[StrictStr] = None
    location_requirement: Optional[StrictStr] = None
    seniority: Optional[StrictStr] = None
    red_flags: list[StrictStr] = Field(default_factory=list)

    @field_validator(
        "must_have_skills",
        "nice_to_have_skills",
        "responsibilities",
        "experience_requirements",
        "education_requirements",
        "red_flags",
    )
    @classmethod
    def _normalize_lists(cls, values: list[StrictStr]) -> list[str]:
        return _clean_string_list(values)

    @field_validator("role_summary", "work_authorization", "location_requirement", "seniority")
    @classmethod
    def _normalize_optional_text(cls, value: Optional[StrictStr]) -> Optional[str]:
        if value is None:
            return None

        stripped = value.strip()
        if not stripped:
            raise ValueError("Text fields must not be empty.")
        return stripped


class JobAnalysisResponse(BaseModel):
    profile_id: str
    job_id: str
    job_requirement_id: str
    analyzed_by: str
    status: str = "analyzed"
    structured_json: JobRequirementPayload

