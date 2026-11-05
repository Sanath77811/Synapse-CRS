"""Map each experiment mode to a three-class label. Tasks are documented."""

from synapse_reasoning.features import extract_features
from synapse_reasoning.hybrid import assess
from synapse_reasoning.neural import score_features
from synapse_reasoning.symbolic import evaluate_rules


def _select_id(support: dict[str, float]) -> str:
    ranked = sorted(support.items(), key=lambda item: item[1], reverse=True)
    best = ranked[0][1]
    tied = [name for name, score in ranked if score == best]
    if "H4_insufficient_evidence" in tied:
        return "H4_insufficient_evidence"
    if "H1_normal" in tied:
        return "H1_normal"
    return ranked[0][0]


HYPOTHESIS_CLASS = {
    "H1_normal": "typical",
    "H2_unusual_legitimate": "unusual_volume",
    "H3_suspicious_pattern": "unusual_volume",
    "H4_insufficient_evidence": "insufficient",
}

VOLUME_FINDINGS = {
    "repeated_network_activity",
    "multi_port_network_activity",
    "rapid_activity_burst",
    "repeated_observation_pattern",
}
GAP_FINDINGS = {"lifecycle_exit_without_start", "lifecycle_pid_reuse_unresolved"}


def correlation_class(reconstruction) -> str:
    types = {item.finding_type for item in reconstruction.findings}
    if types & GAP_FINDINGS:
        return "insufficient"
    if types & VOLUME_FINDINGS:
        return "unusual_volume"
    return "typical"


def neural_class(reconstruction, window_seconds: int = 300) -> str:
    features = extract_features(reconstruction, window_seconds=window_seconds)
    if score_features(features).unusual:
        return "unusual_volume"
    return "typical"


def symbolic_class(reconstruction, window_seconds: int = 300) -> str:
    features = extract_features(reconstruction, window_seconds=window_seconds)
    hits = evaluate_rules(reconstruction, features)
    support = {
        "H1_normal": 0.0,
        "H2_unusual_legitimate": 0.0,
        "H3_suspicious_pattern": 0.0,
        "H4_insufficient_evidence": 0.0,
    }
    for hit in hits:
        support[hit.hypothesis] = max(support[hit.hypothesis], hit.support)
    return HYPOTHESIS_CLASS[_select_id(support)]


def hybrid_class(reconstruction, window_seconds: int = 300) -> str:
    assessment = assess(reconstruction, window_seconds=window_seconds, fingerprint="eval")
    return HYPOTHESIS_CLASS[assessment.selected_hypothesis]


def hybrid_without_quality_class(reconstruction, window_seconds: int = 300) -> str:
    """Ablation: skip reconstruction-completeness promotion of H4."""
    features = extract_features(reconstruction, window_seconds=window_seconds)
    neural = score_features(features)
    hits = evaluate_rules(reconstruction, features)
    support = {
        "H1_normal": 0.0,
        "H2_unusual_legitimate": 0.0,
        "H3_suspicious_pattern": 0.0,
        "H4_insufficient_evidence": 0.0,
    }
    for hit in hits:
        support[hit.hypothesis] = max(support[hit.hypothesis], hit.support)
    if neural.unusual:
        support["H3_suspicious_pattern"] = max(support["H3_suspicious_pattern"], 0.6)
        support["H2_unusual_legitimate"] = max(support["H2_unusual_legitimate"], 0.5)
    else:
        support["H1_normal"] = max(support["H1_normal"], 0.65)
    return HYPOTHESIS_CLASS[_select_id(support)]


def neural_symbolic_class(reconstruction, window_seconds: int = 300) -> str:
    """Neural plus symbolic without the hybrid completeness gate."""
    return hybrid_without_quality_class(reconstruction, window_seconds=window_seconds)
