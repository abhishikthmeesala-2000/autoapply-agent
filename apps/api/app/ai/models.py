from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StrictJsonResponse(BaseModel):
    payload: dict


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage] = Field(default_factory=list)
    temperature: float = 0.0
    format: Optional[str] = "json"
