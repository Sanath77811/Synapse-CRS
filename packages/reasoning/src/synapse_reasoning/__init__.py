"""Hybrid neuro-symbolic reasoning foundation for Synapse-CRS.

This package reconstructs enrolled telemetry, scores versioned features with
an Isolation Forest fitted from a documented synthetic baseline (not a
pickled production detector), evaluates inspectable symbolic rules, and
records predictions, counterfactuals, and Z3 policy checks. It does not
execute mitigations or modify stored telemetry.
"""

ENGINE_VERSION = "0.6.0"
FEATURE_VERSION = "1.0.0"
RULE_VERSION = "1.0.0"
POLICY_VERSION = "1.0.0"
MODEL_ID = "isolation-forest-synthetic-baseline-v1"

__all__ = [
    "ENGINE_VERSION",
    "FEATURE_VERSION",
    "MODEL_ID",
    "POLICY_VERSION",
    "RULE_VERSION",
]
