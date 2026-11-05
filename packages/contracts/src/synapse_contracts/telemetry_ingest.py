"""HTTP telemetry ingestion contracts.

The signature is detached. The envelope is the Phase 1 document. Callers
cannot supply verification or identity labels.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from synapse_telemetry.envelope import TelemetryEnvelope
from synapse_telemetry.signatures import SIGNATURE_PATTERN

from synapse_contracts.version import CONTRACT_VERSION

SignatureText = Annotated[str, Field(pattern=SIGNATURE_PATTERN, min_length=88, max_length=88)]


class TelemetryIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    envelope: TelemetryEnvelope
    signature: SignatureText


class TelemetryIngestView(BaseModel):
    event_id: UUID
    persistence_status: Literal["stored", "duplicate"]
    signature_verified: bool
    identity_status: Literal["enrolled"]
    event_type: str
    agent_id: UUID
    target_id: UUID
    received_at: datetime
    contract_version: str = CONTRACT_VERSION
