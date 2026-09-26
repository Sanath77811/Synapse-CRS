"""Versioned Synapse-CRS contracts shared by the API and tests."""

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
from synapse_contracts.version import API_VERSION, CONTRACT_VERSION

__all__ = [
    "API_VERSION",
    "CONTRACT_VERSION",
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
    "EligibilityView",
    "ErrorBody",
    "ErrorResponse",
    "TargetCreate",
    "TargetPage",
    "TargetScope",
    "TargetView",
    "TransitionView",
]
