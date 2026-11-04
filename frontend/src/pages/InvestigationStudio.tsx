import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiRequest } from "../api/client";
import type { CaseDetail } from "../api/types";
import { Timeline } from "../components/Timeline";
import { usePlatformContext } from "../context/PlatformContext";
import { demoCase } from "../data/demo";
import { formatTime, shortId } from "../lib/format";

const ORDER = [
  "AUTHORIZED_TARGET",
  "OBSERVATION",
  "EVIDENCE",
  "HYPOTHESIS",
  "VERIFICATION",
  "APPROVAL",
  "ACTION",
  "VALIDATION",
  "ROLLBACK",
  "SEALED_AUDIT",
];

const NEXT: Record<string, string | null> = Object.fromEntries(
  ORDER.map((item, index) => [item, ORDER[index + 1] ?? null]),
);

export function InvestigationStudio() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { data, mode, token } = usePlatformContext();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [reason, setReason] = useState("Advance stored pipeline state only");
  const [message, setMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState("");
  useEffect(() => {
    const id = caseId ?? data.cases[0]?.id;
    if (!id) {
      setDetail(null);
      return;
    }
    if (mode === "demo") {
      setDetail(id === demoCase.id ? demoCase : null);
      return;
    }
    if (!token) {
      return;
    }
    const controller = new AbortController();
    void apiRequest<CaseDetail>(`/api/v1/cases/${id}`, { token, signal: controller.signal })
      .then(setDetail)
      .catch((err: Error) => setMessage(err.message));
    return () => controller.abort();
  }, [caseId, data.cases, mode, token]);

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

  const current = detail;
  return (
    <div className="dossier">
      <aside className="dos-list">
        <h2>Dockets</h2>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="filter state or id…"
          aria-label="Filter cases"
        />
        {data.cases
          .filter((item) => {
            const q = filter.trim().toLowerCase();
            return !q || item.state.toLowerCase().includes(q) || item.id.toLowerCase().includes(q);
          })
          .map((item) => (
          <button
            type="button"
            key={item.id}
            className={item.id === current?.id ? "dock is-on" : "dock"}
            onClick={() => navigate(`/investigations/${item.id}`)}
          >
            <b>{item.state}</b>
            <span className="mono">{shortId(item.id)}</span>
            <span className="dim">{formatTime(item.updated_at)}</span>
          </button>
        ))}
        {data.cases.length === 0 ? <p className="dim">No cases.</p> : null}
      </aside>
      <section className="dos-main">
        {current ? (
          <>
            <header className="dos-id">
              <p className="kicker">Investigation studio</p>
              <h1>Case {shortId(current.id)}</h1>
              <p className="dim">ACTION stores a label. It does not change a host.</p>
            </header>
            <ol className="state-track">
              {ORDER.map((state) => (
                <li key={state} className={state === current.state ? "is-now" : undefined}>
                  {state.replaceAll("_", " ")}
                </li>
              ))}
            </ol>
            <div className="dos-split">
              <div>
                <h2>Activity</h2>
                <ol className="timeline">
                  {current.transitions.map((item) => (
                    <li key={item.id} className="tl tl-observed">
                      <div className="tl-meta">
                        <span className="mono">{formatTime(item.created_at)}</span>
                        <span>
                          {item.from_state} → {item.to_state}
                        </span>
                      </div>
                      <p>{item.reason}</p>
                      <p className="dim">executed={String(item.executed)}</p>
                    </li>
                  ))}
                </ol>
              </div>
              <div>
                <h2>Linked evidence</h2>
                <p className="dim">Findings in the current snapshot, not a private case join table.</p>
                {data.findings.map((item) => (
                  <p key={item.id}>{item.finding_type.replaceAll("_", " ")}</p>
                ))}
                {data.timeline ? <Timeline items={data.timeline.timeline.slice(0, 4)} /> : null}
              </div>
            </div>
            {message ? <p className="dim">{message}</p> : null}
            <div className="row-actions">
              <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={200} />
              <button type="button" className="primary" onClick={() => void advance()}>
                Next stored state {NEXT[current.state] ?? "—"}
              </button>
            </div>
          </>
        ) : (
          <p className="dim pad">Select a docket.</p>
        )}
      </section>
    </div>
  );
}
