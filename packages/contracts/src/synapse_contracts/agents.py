"""Agent enrollment contracts.

Enrollment is an administrator action. A registered public key is not a
private key and is not an authorization token.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from synapse_contracts.version import CONTRACT_VERSION

PublicKeyHex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)]


class AgentEnroll(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_key_hex: PublicKeyHex
    agent_id: UUID | None = None


class AgentKeyRotate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_key_hex: PublicKeyHex


class AgentView(BaseModel):
    id: UUID
    target_id: UUID
    public_key_hex: str
    public_key_fingerprint: str
    key_generation: int
    status: str
    enrolled_at: datetime
    enrolled_by: str
    revoked_at: datetime | None
    updated_at: datetime
    contract_version: str = CONTRACT_VERSION


class AgentPage(BaseModel):
    items: list[AgentView]
    limit: int
    offset: int
    total: int
