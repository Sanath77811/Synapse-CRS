"""Case pipeline contracts.

The states name pipeline stages. A transition in v0.1 changes stored state
and writes an audit event. It does not observe, analyze, or change a host.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from synapse_contracts.text import BoundedReason
from synapse_contracts.version import CONTRACT_VERSION


class CaseState(StrEnum):
    AUTHORIZED_TARGET = "AUTHORIZED_TARGET"
    OBSERVATION = "OBSERVATION"
    EVIDENCE = "EVIDENCE"
    HYPOTHESIS = "HYPOTHESIS"
    VERIFICATION = "VERIFICATION"
    APPROVAL = "APPROVAL"
    ACTION = "ACTION"
    VALIDATION = "VALIDATION"
    ROLLBACK = "ROLLBACK"
    SEALED_AUDIT = "SEALED_AUDIT"


class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: UUID
    reason: BoundedReason


class CaseTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_state: CaseState
    reason: BoundedReason


class TransitionView(BaseModel):
    id: UUID
    case_id: UUID
    from_state: CaseState
    to_state: CaseState
    actor: str
    reason: str
    created_at: datetime
    executed: bool = Field(
        default=False,
        description="v0.1 never executes a security action. This value is always false.",
    )


class CaseView(BaseModel):
    id: UUID
    target_id: UUID
    state: CaseState
    created_at: datetime
    updated_at: datetime
    created_by: str
    contract_version: str = CONTRACT_VERSION


class CaseDetail(CaseView):
    transitions: list[TransitionView]


class CasePage(BaseModel):
    items: list[CaseView]
    limit: int
    offset: int
    total: int
