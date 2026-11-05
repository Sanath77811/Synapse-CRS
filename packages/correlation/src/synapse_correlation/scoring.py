"""Transparent preliminary risk score. Severity is derived after scoring.

This is a research heuristic over correlation findings. It is not a
probability of compromise and it is not a machine-learning model.

Formula
-------
score = min(100, sum of capped factor groups)

Groups and weights (points):

* lifecycle_exit_without_start: 15 per finding, group cap 30
* lifecycle_pid_reuse_unresolved: 25 per finding, group cap 50
* repeated_network_activity: 4 per connection above threshold 5, per
  finding, group cap 20
* multi_port_network_activity: 5 per remote port above threshold 3, per
  finding, group cap 20
* rapid_activity_burst: 3 per event above threshold 8, per finding,
  group cap 20
* repeated_observation_pattern: 15 per finding, group cap 15

A process that starts, makes one or two connections, and exits scores 0.

Severity bands (separate from confidence):

* 0–19 info
* 20–39 low
* 40–69 medium
* 70–100 high

High severity means "this heuristic asked for attention". It does not mean
the host is compromised.
"""

from synapse_correlation.models import Finding, RiskFactor, RiskSummary, Severity

FORMULA = (
    "min(100, cap(exit_without_start,30) + cap(pid_reuse,50) + "
    "cap(repeated_network,20) + cap(multi_port,20) + cap(rapid_burst,20) + "
    "cap(repeated_pattern,15))"
)

ROLLUP_CAPS = {
    "lifecycle_exit_without_start": 30,
    "lifecycle_pid_reuse_unresolved": 50,
    "repeated_network_activity": 20,
    "multi_port_network_activity": 20,
    "rapid_activity_burst": 20,
    "repeated_observation_pattern": 15,
}


def severity_for_score(score: int) -> Severity:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "info"


def score_findings(findings: tuple[Finding, ...]) -> RiskSummary:
    grouped: dict[str, int] = {name: 0 for name in ROLLUP_CAPS}
    factors: list[RiskFactor] = []
    for finding in findings:
        grouped[finding.finding_type] = grouped.get(finding.finding_type, 0) + (
            finding.risk_contribution
        )
        factors.extend(finding.risk_factors)
    capped: list[RiskFactor] = []
    total = 0
    for code, cap in ROLLUP_CAPS.items():
        raw = grouped.get(code, 0)
        points = min(raw, cap)
        if points:
            capped.append(RiskFactor(code=code, points=points, detail=f"raw={raw} cap={cap}"))
            total += points
    score = min(100, total)
    return RiskSummary(
        score=score,
        factors=tuple(capped),
        finding_count=len(findings),
        formula=FORMULA,
    )
