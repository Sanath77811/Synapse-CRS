"""Versioned Synapse-CRS contracts shared by the API and tests."""

from synapse_contracts.agents import AgentEnroll, AgentKeyRotate, AgentPage, AgentView
from synapse_contracts.audit import AuditEventView, ChainVerificationView
from synapse_contracts.cases import (
    CaseCreate,
    CaseDetail,
    CasePage,
    CaseState,
    CaseTransitionRequest,
    CaseView,
    TransitionView,
)
from synapse_contracts.correlation import (
    CorrelationLinkPage,
    CorrelationLinkView,
    CorrelationRunRequest,
    CorrelationRunView,
    FindingPage,
    FindingView,
    RiskSummaryView,
)
from synapse_contracts.errors import ErrorBody, ErrorResponse
from synapse_contracts.targets import (
    AuthorizationStatus,
    Capability,
    EligibilityView,
    TargetCreate,
    TargetPage,
    TargetScope,
    TargetView,
)
from synapse_contracts.telemetry_ingest import TelemetryIngestRequest, TelemetryIngestView
from synapse_contracts.version import API_VERSION, CONTRACT_VERSION

__all__ = [
    "API_VERSION",
    "CONTRACT_VERSION",
    "AgentEnroll",
    "AgentKeyRotate",
    "AgentPage",
    "AgentView",
    "AuditEventView",
    "AuthorizationStatus",
    "Capability",
    "CaseCreate",
    "CaseDetail",
    "CasePage",
    "CaseState",
    "CaseTransitionRequest",
    "CaseView",
    "ChainVerificationView",
    "CorrelationLinkPage",
    "CorrelationLinkView",
    "CorrelationRunRequest",
    "CorrelationRunView",
    "FindingPage",
    "FindingView",
    "RiskSummaryView",
    "EligibilityView",
    "ErrorBody",
    "ErrorResponse",
    "TargetCreate",
    "TargetPage",
    "TargetScope",
    "TargetView",
    "TelemetryIngestRequest",
    "TelemetryIngestView",
    "TransitionView",
]
