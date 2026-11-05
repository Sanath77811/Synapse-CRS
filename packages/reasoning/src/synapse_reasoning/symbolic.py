"""Inspectable symbolic rules. Logic lives in the rule table, not ad-hoc ifs."""

from synapse_reasoning import RULE_VERSION
from synapse_reasoning.models import Reconstruction, SymbolicHit

RULES: tuple[dict[str, object], ...] = (
    {
        "id": "sym.normal_lifecycle",
        "version": RULE_VERSION,
        "description": "A complete process lifetime with few covering networks.",
        "required": ("process_started", "process_exited"),
        "conditions": {"max_network_per_process_lt": 3, "missing_start_eq": 0},
        "hypothesis": "H1_normal",
        "support": 0.7,
        "limitations": "Does not prove the process is benign.",
    },
    {
        "id": "sym.repeated_network",
        "version": RULE_VERSION,
        "description": "Phase 8 repeated_network_activity finding is present.",
        "required": ("repeated_network_activity",),
        "conditions": {"has_finding": "repeated_network_activity"},
        "hypothesis": "H3_suspicious_pattern",
        "support": 0.75,
        "limitations": "Volume correlation is not intent.",
    },
    {
        "id": "sym.multi_port",
        "version": RULE_VERSION,
        "description": "Phase 8 multi_port_network_activity finding is present.",
        "required": ("multi_port_network_activity",),
        "conditions": {"has_finding": "multi_port_network_activity"},
        "hypothesis": "H3_suspicious_pattern",
        "support": 0.7,
        "limitations": "Distinct ports may be ordinary client behaviour.",
    },
    {
        "id": "sym.pid_reuse_gap",
        "version": RULE_VERSION,
        "description": "Unresolved PID reuse or exit without start.",
        "required": (),
        "conditions": {
            "any_finding": (
                "lifecycle_pid_reuse_unresolved",
                "lifecycle_exit_without_start",
            )
        },
        "hypothesis": "H4_insufficient_evidence",
        "support": 0.8,
        "limitations": "Identity gaps reduce reconstructability, not prove an attack.",
    },
    {
        "id": "sym.unusual_but_complete",
        "version": RULE_VERSION,
        "description": "Findings exist on a complete lifecycle; may be legitimate load.",
        "required": ("process_started", "process_exited"),
        "conditions": {
            "has_any_finding": True,
            "complete_lifecycle": True,
        },
        "hypothesis": "H2_unusual_legitimate",
        "support": 0.55,
        "limitations": "Cannot distinguish lab load from hostile automation.",
    },
    {
        "id": "sym.sparse_evidence",
        "version": RULE_VERSION,
        "description": "Fewer than three observations.",
        "required": (),
        "conditions": {"max_events_lt": 3},
        "hypothesis": "H4_insufficient_evidence",
        "support": 0.9,
        "limitations": "Absence of evidence is not evidence of absence.",
    },
)


def evaluate_rules(reconstruction: Reconstruction, features) -> tuple[SymbolicHit, ...]:
    finding_types = {item.finding_type for item in reconstruction.findings}
    hits: list[SymbolicHit] = []
    for rule in RULES:
        if not _matches(rule, reconstruction, features, finding_types):
            continue
        event_ids = []
        for finding in reconstruction.findings:
            required = rule.get("required", ())
            if finding.finding_type in required or rule["conditions"].get("has_finding") == (
                finding.finding_type
            ):
                event_ids.extend(finding.supporting_event_ids)
        if not event_ids:
            event_ids = list(reconstruction.supporting_event_ids[:8])
        missing = []
        required = rule.get("required", ())
        for name in required:
            if name in {"process_started", "process_exited"}:
                types = {item.event_type for item in reconstruction.observations}
                if name not in types:
                    missing.append(name)
            elif name not in finding_types and name not in {
                item.event_type for item in reconstruction.observations
            }:
                missing.append(str(name))
        hits.append(
            SymbolicHit(
                rule_id=str(rule["id"]),
                rule_version=str(rule["version"]),
                hypothesis=rule["hypothesis"],  # type: ignore[arg-type]
                support=float(rule["support"]),
                evidence_event_ids=tuple(dict.fromkeys(event_ids)),
                missing=tuple(missing),
                description=str(rule["description"]),
            )
        )
    return tuple(hits)


def _matches(rule: dict[str, object], reconstruction, features, finding_types: set[str]) -> bool:
    conditions = rule["conditions"]
    assert isinstance(conditions, dict)
    if "max_network_per_process_lt" in conditions:
        if features.values["max_network_per_process"] >= float(
            conditions["max_network_per_process_lt"]
        ):
            return False
    if "missing_start_eq" in conditions:
        if features.values["missing_start_count"] != float(conditions["missing_start_eq"]):
            return False
    if "has_finding" in conditions:
        if conditions["has_finding"] not in finding_types:
            return False
    if "any_finding" in conditions:
        wanted = conditions["any_finding"]
        if not any(name in finding_types for name in wanted):  # type: ignore[union-attr]
            return False
    if conditions.get("has_any_finding"):
        if not reconstruction.findings:
            return False
    if conditions.get("complete_lifecycle"):
        if features.values["complete_lifecycle_ratio"] < 1.0:
            return False
    if "max_events_lt" in conditions:
        if len(reconstruction.observations) >= int(conditions["max_events_lt"]):
            return False
    required = rule.get("required", ())
    types = {item.event_type for item in reconstruction.observations}
    for name in required:  # type: ignore[union-attr]
        if name in {"process_started", "process_exited"} and name not in types:
            return False
    return True
