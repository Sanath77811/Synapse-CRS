"""Stable finding identity for idempotent persistence."""

import hashlib
import json


def finding_fingerprint(material: dict[str, str]) -> str:
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
