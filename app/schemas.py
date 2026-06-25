from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict


Channel = Literal["email", "form", "chat"]
Category = Literal["billing", "support", "complaint", "other"]
Confidence = Literal["high", "medium", "low"]


class TriageRequest(BaseModel):
    """Incoming request contract for POST /triage."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(..., min_length=1, max_length=2000, description="Customer message text")
    channel: Channel = Field(..., description="Source channel label")
    client_id: str = Field(..., min_length=1, max_length=128, description="Client identifier for audit and rate limiting")

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_.:@-]{1,128}", value):
            raise ValueError("client_id may contain only letters, digits, dot, underscore, colon, @ or hyphen")
        return value


class TriageResult(BaseModel):
    """Strict LLM result after guardrail validation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: Category
    draft_reply: str = Field(..., min_length=1, max_length=2000)
    confidence: Confidence
    escalate: bool

    @field_validator("draft_reply")
    @classmethod
    def validate_reply_sentence_count(cls, value: str) -> str:
        # Approximate sentence counting for Russian/English drafts.
        fragments = [p for p in re.split(r"[.!?。！？]+", value) if p.strip()]
        if not 1 <= len(fragments) <= 6:
            raise ValueError("draft_reply must contain 1-6 sentences")
        return value

    @field_validator("escalate")
    @classmethod
    def normalize_low_confidence_escalation(cls, value: bool, info) -> bool:
        # Safety rule: low confidence must always be escalated.
        # In Pydantic v2 field order makes confidence already available here.
        confidence = info.data.get("confidence")
        if confidence == "low":
            return True
        return value


class TriageResponse(TriageResult):
    """Public API response."""


class TicketRecord(BaseModel):
    """Internal object saved to SQLite."""

    client_id: str
    channel: Channel
    text: str
    category: Category
    confidence: Confidence
    escalate: bool
    draft_reply: str
    error: str | None = None
