"""Phase 12 independent endpoint-evidence research track.

External process traces are never enrolled Linux telemetry. Sample-level
malware labels are never treated as event-level ground truth. Phase 9
hybrid reconstruction is not comparable unless source identity fields
match the Linux (agent_id, boot_id, pid, start_ticks) model.
"""

PHASE12_VERSION = "0.9.0"
EXPERIMENT_ID = "phase12-endpoint-evidence-v1"
NORMALIZATION_VERSION = "endpoint-evidence-1.0.0"

__all__ = ["EXPERIMENT_ID", "NORMALIZATION_VERSION", "PHASE12_VERSION"]
