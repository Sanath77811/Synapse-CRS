import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import type { CaseDetail, CaseView } from "../api/types";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";
import { demoCase } from "../data/demo";
import { formatTime, shortId } from "../lib/format";

const NEXT: Record<string, string | null> = {
  AUTHORIZED_TARGET: "OBSERVATION",
  OBSERVATION: "EVIDENCE",
  EVIDENCE: "HYPOTHESIS",
  HYPOTHESIS: "VERIFICATION",
  VERIFICATION: "APPROVAL",
  APPROVAL: "ACTION",
  ACTION: "VALIDATION",
  VALIDATION: "ROLLBACK",
  ROLLBACK: "SEALED_AUDIT",
  SEALED_AUDIT: null,
};

export function InvestigationStudio() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { data, mode, token } = usePlatformContext();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [reason, setReason] = useState("Advance stored pipeline state only");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) {
      setDetail(null);
      return;
    }
    if (mode === "demo") {
      setDetail(caseId === demoCase.id ? demoCase : null);
      return;
    }
    if (!token) {
      return;
    }
    const controller = new AbortController();
    void apiRequest<CaseDetail>(`/api/v1/cases/${caseId}`, { token, signal: controller.signal })
      .then(setDetail)
      .catch((err: Error) => setMessage(err.message));
    return () => controller.abort();
  }, [caseId, mode, token]);

  async function advance() {
    if (!detail || mode !== "live" || !token) {
      setMessage("Transitions against the API require a live admin session.");
      return;
    }
    const next = NEXT[detail.state];
    if (!next) {
      setMessage("Case is terminal.");
      return;
    }
    try {
      const updated = await apiRequest<CaseDetail>(`/api/v1/cases/${detail.id}/transitions`, {
        token,
        method: "POST",
        body: { to_state: next, reason },
      });
      setDetail(updated);
      setMessage(`Stored state is now ${updated.state}. executed remains false.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Transition rejected");
    }
  }

  return (
    <div className="page">
      <PageHeader
        kicker="Investigation Studio"
        title="Case pipeline"
        summary="States are stored pipeline labels. Entering ACTION does not execute a host action."
      />
      <section className="panel">
        <h2>Cases</h2>
        <DataTable
          rows={data.cases}
          selectedId={caseId}
          onSelect={(row: CaseView) => navigate(`/investigations/${row.id}`)}
          empty="No cases."
          columns={[
            { key: "state", header: "State", render: (row) => <StatusChip label={row.state} /> },
            { key: "target", header: "Target", mono: true, render: (row) => shortId(row.target_id) },
            { key: "updated", header: "Updated", render: (row) => formatTime(row.updated_at) },
          ]}
        />
      </section>
      {detail ? (
        <section className="panel">
          <h2>Case {shortId(detail.id)}</h2>
          <p>
            <StatusChip label={detail.state} /> next {NEXT[detail.state] ?? "none"}
          </p>
          <ol className="timeline">
            {detail.transitions.map((item) => (
              <li key={item.id} className="tl tl-observed">
                <div className="tl-meta">
                  <span className="mono">{formatTime(item.created_at)}</span>
                  <span className="chip chip-info">{item.from_state} → {item.to_state}</span>
                </div>
                <p>{item.reason}</p>
                <p className="muted">executed={String(item.executed)} · {item.actor}</p>
              </li>
            ))}
          </ol>
          {message ? <p className="muted">{message}</p> : null}
          <div className="row-actions">
            <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={200} />
            <button type="button" className="primary" onClick={() => void advance()}>
              Request next stored transition
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
