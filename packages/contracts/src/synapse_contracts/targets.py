"""Target registry contracts."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from synapse_contracts.capabilities import Capability
from synapse_contracts.scope import TargetScope
from synapse_contracts.text import BoundedName, reject_unbounded_text
from synapse_contracts.version import CONTRACT_VERSION

AuthorizationStatus = Annotated[
    str,
    Field(pattern="^(active|revoked|expired|invalid)$"),
]


class TargetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: BoundedName
    owner: BoundedName
    scope: TargetScope
    authorization_expiry: datetime
    allowed_capabilities: Annotated[list[Capability], Field(min_length=1, max_length=8)]

    @field_validator("name", "owner")
    @classmethod
    def bounded_identity(cls, value: str) -> str:
        return reject_unbounded_text(value)

    @field_validator("authorization_expiry")
    @classmethod
    def aware_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorization_expiry must be timezone-aware")
        return value

    @field_validator("allowed_capabilities")
    @classmethod
    def unique_capabilities(cls, value: list[Capability]) -> list[Capability]:
        if len(set(value)) != len(value):
            raise ValueError("allowed_capabilities must be unique")
        return value


class TargetView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    name: str
    owner: str
    scope: TargetScope
    authorization_status: str
    authorization_expiry: datetime
    allowed_capabilities: list[Capability]
    eligible: bool
    eligibility_reasons: list[str]
    created_at: datetime
    updated_at: datetime
    contract_version: str = CONTRACT_VERSION


class TargetPage(BaseModel):
    items: list[TargetView]
    limit: int
    offset: int
    total: int


class EligibilityView(BaseModel):
    target_id: UUID
    eligible: bool
    authorization_status: str
    reasons: list[str]
    evaluated_at: datetime
    contract_version: str = CONTRACT_VERSION
