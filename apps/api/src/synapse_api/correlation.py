"""Load enrolled evidence, correlate it, and persist derived rows."""

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from synapse_contracts.correlation import (
    CorrelationLinkPage,
    CorrelationLinkView,
    CorrelationRunView,
    FindingPage,
    FindingView,
    RiskFactorView,
    RiskSummaryView,
    SupportingEventView,
)
from synapse_contracts.version import CONTRACT_VERSION
from synapse_correlation.engine import CorrelationConfig, correlate
from synapse_correlation.fingerprint import finding_fingerprint
from synapse_correlation.observations import observation_from_envelope
from synapse_correlation.scoring import FORMULA

from synapse_api.audit_log import append_event
from synapse_api.clock import utc_now
from synapse_api.errors import ApiError
from synapse_api.models import (
    CorrelationLinkRow,
    CorrelationRunRow,
    FindingRow,
    TargetRow,
    TelemetryEventRow,
)


def run_correlation(
    session: Session,
    target_id: UUID,
    *,
    window_seconds: int,
    actor: str,
) -> CorrelationRunView:
    target = (
        session.execute(select(TargetRow).where(TargetRow.id == target_id).with_for_update())
        .scalars()
        .one_or_none()
    )
    if target is None:
        raise ApiError(404, "target_not_found", "Target was not found.")
    rows = list(
        session.execute(
            select(TelemetryEventRow)
            .where(
                TelemetryEventRow.target_id == target_id,
                TelemetryEventRow.identity_status == "enrolled",
            )
            .order_by(TelemetryEventRow.observed_at.desc(), TelemetryEventRow.event_id.desc())
            .limit(5000)
        ).scalars()
    )
    observations = tuple(observation_from_envelope(row.envelope) for row in rows)
    now = utc_now()
    result = correlate(
        observations,
        CorrelationConfig(window_seconds=window_seconds),
        created_at=now,
    )
    run_id = uuid4()
    session.add(
        CorrelationRunRow(
            id=run_id,
            target_id=target_id,
            window_seconds=window_seconds,
            event_count=result.event_count,
            link_count=len(result.links),
            finding_count=len(result.findings),
            risk_score=result.risk.score,
            risk_factors=[
                {"code": item.code, "points": item.points, "detail": item.detail}
                for item in result.risk.factors
            ],
            formula=result.risk.formula,
            actor=actor,
            created_at=now,
        )
    )
    session.flush()
    for link in result.links:
        session.execute(
            insert(CorrelationLinkRow)
            .values(
                id=uuid4(),
                run_id=run_id,
                target_id=link.target_id,
                rule_id=link.rule_id,
                left_event_id=link.left_event_id,
                right_event_id=link.right_event_id,
                agent_id=link.agent_id,
                boot_id=link.boot_id,
                process_pid=link.process_pid,
                process_start_ticks=link.process_start_ticks,
                window_seconds=link.window_seconds,
                reason=link.reason,
                left_observed_at=link.left_observed_at,
                right_observed_at=link.right_observed_at,
            )
            .on_conflict_do_nothing(
                constraint="correlation_links_pair_key",
            )
        )
    for finding in result.findings:
        fingerprint = finding_fingerprint(finding.fingerprint_material)
        existing = session.execute(
            select(FindingRow).where(FindingRow.fingerprint == fingerprint).with_for_update()
        ).scalar_one_or_none()
        payload = dict(
            target_id=finding.target_id,
            agent_id=finding.agent_id,
            boot_id=finding.boot_id,
            finding_type=finding.finding_type,
            severity=finding.severity,
            evidence_strength=finding.evidence_strength,
            confidence=finding.confidence,
            epistemic_status=finding.epistemic_status,
            supporting_event_ids=[str(item) for item in finding.supporting_event_ids],
            explanation=finding.explanation,
            rules_triggered=list(finding.rules_triggered),
            missing_evidence=list(finding.missing_evidence),
            risk_contribution=finding.risk_contribution,
            risk_factors=[
                {"code": item.code, "points": item.points, "detail": item.detail}
                for item in finding.risk_factors
            ],
            subject_key=finding.subject_key,
            window_seconds=finding.window_seconds,
            last_run_id=run_id,
            updated_at=now,
        )
        if existing is None:
            session.add(
                FindingRow(
                    id=uuid4(),
                    fingerprint=fingerprint,
                    created_at=now,
                    **payload,
                )
            )
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
    append_event(
        session,
        actor=actor,
        event_type="correlation.completed",
        target_id=target_id,
        case_id=None,
        payload={
            "run_id": str(run_id),
            "finding_count": len(result.findings),
            "link_count": len(result.links),
            "risk_score": result.risk.score,
            "window_seconds": window_seconds,
        },
        timestamp=now,
    )
    return CorrelationRunView(
        id=run_id,
        target_id=target_id,
        window_seconds=window_seconds,
        event_count=result.event_count,
        link_count=len(result.links),
        finding_count=len(result.findings),
        risk=_risk_view(
            result.risk.score,
            result.risk.factors,
            len(result.findings),
            result.risk.formula,
        ),
        created_at=now,
        actor=actor,
        contract_version=CONTRACT_VERSION,
    )


def list_findings(session: Session, target_id: UUID, limit: int, offset: int) -> FindingPage:
    _require_target(session, target_id)
    total = session.execute(
        select(func.count()).select_from(FindingRow).where(FindingRow.target_id == target_id)
    ).scalar_one()
    rows = session.execute(
        select(FindingRow)
        .where(FindingRow.target_id == target_id)
        .order_by(FindingRow.created_at.desc(), FindingRow.id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars()
    items = [_finding_view(session, row) for row in rows]
    return FindingPage(items=items, limit=limit, offset=offset, total=total)


def get_finding(session: Session, finding_id: UUID) -> FindingView:
    row = session.get(FindingRow, finding_id)
    if row is None:
        raise ApiError(404, "finding_not_found", "Finding was not found.")
    return _finding_view(session, row)


def list_links(session: Session, target_id: UUID, limit: int, offset: int) -> CorrelationLinkPage:
    _require_target(session, target_id)
    total = session.execute(
        select(func.count())
        .select_from(CorrelationLinkRow)
        .where(CorrelationLinkRow.target_id == target_id)
    ).scalar_one()
    rows = session.execute(
        select(CorrelationLinkRow)
        .where(CorrelationLinkRow.target_id == target_id)
        .order_by(CorrelationLinkRow.left_observed_at.desc(), CorrelationLinkRow.id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars()
    items = [
        CorrelationLinkView(
            id=row.id,
            rule_id=row.rule_id,
            left_event_id=row.left_event_id,
            right_event_id=row.right_event_id,
            agent_id=row.agent_id,
            boot_id=row.boot_id,
            process_pid=row.process_pid,
            process_start_ticks=row.process_start_ticks,
            window_seconds=row.window_seconds,
            reason=row.reason,
            left_observed_at=row.left_observed_at,
            right_observed_at=row.right_observed_at,
        )
        for row in rows
    ]
    return CorrelationLinkPage(items=items, limit=limit, offset=offset, total=total)


def risk_summary(session: Session, target_id: UUID) -> RiskSummaryView:
    _require_target(session, target_id)
    run = session.execute(
        select(CorrelationRunRow)
        .where(CorrelationRunRow.target_id == target_id)
        .order_by(CorrelationRunRow.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if run is None:
        return RiskSummaryView(
            score=0,
            factors=[],
            finding_count=0,
            formula=FORMULA,
        )
    factors = [
        RiskFactorView(
            code=str(item["code"]),
            points=int(item["points"]),
            detail=str(item["detail"]),
        )
        for item in run.risk_factors
        if isinstance(item, dict)
    ]
    return _risk_view(run.risk_score, factors, run.finding_count, run.formula)


def _require_target(session: Session, target_id: UUID) -> None:
    if session.get(TargetRow, target_id) is None:
        raise ApiError(404, "target_not_found", "Target was not found.")


def _risk_view(score: int, factors, finding_count: int, formula: str) -> RiskSummaryView:
    cleaned: list[RiskFactorView] = []
    for item in factors:
        if isinstance(item, RiskFactorView):
            cleaned.append(item)
            continue
        if hasattr(item, "code"):
            cleaned.append(RiskFactorView(code=item.code, points=item.points, detail=item.detail))
            continue
        cleaned.append(
            RiskFactorView(
                code=str(item["code"]),
                points=int(item["points"]),
                detail=str(item["detail"]),
            )
        )
    return RiskSummaryView(
        score=score,
        factors=cleaned,
        finding_count=finding_count,
        formula=formula,
        contract_version=CONTRACT_VERSION,
    )


def _finding_view(session: Session, row: FindingRow) -> FindingView:
    ids = [UUID(str(item)) for item in row.supporting_event_ids]
    events = []
    if ids:
        stored = session.execute(
            select(TelemetryEventRow).where(TelemetryEventRow.event_id.in_(ids))
        ).scalars()
        by_id = {item.event_id: item for item in stored}
        for event_id in ids:
            item = by_id.get(event_id)
            if item is None:
                continue
            events.append(
                SupportingEventView(
                    event_id=item.event_id,
                    event_type=item.event_type,
                    observed_at=item.observed_at,
                    sequence=item.sequence,
                )
            )
    return FindingView(
        id=row.id,
        target_id=row.target_id,
        finding_type=row.finding_type,  # type: ignore[arg-type]
        severity=row.severity,  # type: ignore[arg-type]
        evidence_strength=row.evidence_strength,  # type: ignore[arg-type]
        confidence=row.confidence,
        epistemic_status=row.epistemic_status,  # type: ignore[arg-type]
        supporting_event_ids=ids,
        supporting_events=events,
        explanation=row.explanation,
        rules_triggered=[str(item) for item in row.rules_triggered],
        missing_evidence=[str(item) for item in row.missing_evidence],
        risk_contribution=row.risk_contribution,
        risk_factors=[
            RiskFactorView(
                code=str(item["code"]),
                points=int(item["points"]),
                detail=str(item["detail"]),
            )
            for item in row.risk_factors
            if isinstance(item, dict)
        ],
        agent_id=row.agent_id,
        boot_id=row.boot_id,
        window_seconds=row.window_seconds,
        created_at=row.created_at,
        updated_at=row.updated_at,
        contract_version=CONTRACT_VERSION,
    )
