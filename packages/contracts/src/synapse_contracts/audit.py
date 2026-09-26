"""Audit event contracts."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from synapse_contracts.version import CONTRACT_VERSION


class AuditEventView(BaseModel):
    id: UUID
    sequence: int = Field(ge=1)
    timestamp: datetime
    actor: str
    event_type: str
    target_id: UUID | None
    case_id: UUID | None
    payload: dict[str, Any]
    previous_event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract_version: str = CONTRACT_VERSION


class AuditEventPage(BaseModel):
    items: list[AuditEventView]
    limit: int
    offset: int
    total: int


class ChainVerificationView(BaseModel):
    valid: bool
    event_count: int = Field(ge=0)
    head_hash: str | None
    failure_sequence: int | None
    failure_reason: str | None
    contract_version: str = CONTRACT_VERSION
