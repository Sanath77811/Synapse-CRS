"""Deterministic evidence correlation for stored telemetry.

This package links verified observations and emits explainable findings.
It does not collect hosts, execute actions, or claim compromise. Findings
are correlations or inferences from stored evidence, not new observations.
"""

from synapse_correlation.engine import CorrelationConfig, CorrelationResult, correlate
from synapse_correlation.models import (
    CorrelationLink,
    Finding,
    Observation,
    ProcessIdentity,
    RiskFactor,
)
from synapse_correlation.scoring import score_findings

__all__ = [
    "CorrelationConfig",
    "CorrelationLink",
    "CorrelationResult",
    "Finding",
    "Observation",
    "ProcessIdentity",
    "RiskFactor",
    "correlate",
    "score_findings",
]
