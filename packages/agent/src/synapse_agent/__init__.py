"""Linux procfs telemetry collector for Synapse-CRS.

The agent observes processes and network table rows, normalizes them with
the existing Phase 3 allowlist, signs with a local Ed25519 key, and POSTs
to the Phase 6 ingest API. It does not enroll itself, execute actions, or
export private keys.
"""

__all__ = ["__version__"]

__version__ = "0.4.0"
