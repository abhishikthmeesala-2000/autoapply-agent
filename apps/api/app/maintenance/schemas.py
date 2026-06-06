from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    profile_id: str
    actor_type: str
    action: str
    entity_type: str
    entity_id: str
    details_json: dict[str, Any]
    created_at: datetime


class BackupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passphrase: str = Field(min_length=12)
    confirm_profile_name: str = Field(min_length=1)


class EncryptedBackupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    file_name: str
    status: str = "exported"
    encrypted: bool = True


class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_profile_name: str = Field(min_length=1)


class DeletionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: str
    status: str = "deleted"
    preserved_audit_logs: int
    deleted_counts: dict[str, int] = Field(default_factory=dict)

