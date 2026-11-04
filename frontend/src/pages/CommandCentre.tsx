import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";
import { RESEARCH_PHASES } from "../data/research";
import { formatTime } from "../lib/format";

export function CommandCentre() {
  const { mode, data, health, ready, selectedTarget, error, state } = usePlatformContext();
  const phases = RESEARCH_PHASES;
  return (
    <div className="page">
      <PageHeader
        kicker="Command Centre"
        title="Investigation operating picture"
        summary="Live control-plane status, registered targets, and research honesty. No autonomous mitigation is available from this console."
      />
      {error ? <p className="error-banner">{error}</p> : null}
      {state === "loading" ? <p className="muted">Loading control-plane snapshot…</p> : null}
      <section className="stat-grid">
        <article className="stat">
          <span>API</span>
          <strong>{health?.status ?? "unknown"}</strong>
          <small>{health?.version ?? "unversioned probe"}</small>
        </article>
        <article className="stat">
          <span>Database</span>
          <strong>{ready?.database ?? ready?.status ?? "unknown"}</strong>
        </article>
        <article className="stat">
          <span>Targets</span>
          <strong>{data.targets.length}</strong>
        </article>
        <article className="stat">
          <span>Agents enrolled</span>
          <strong>{data.agents.length}</strong>
          <small>Enrollment is not proof of recent telemetry</small>
        </article>
        <article className="stat">
          <span>Findings</span>
          <strong>{data.findings.length}</strong>
        </article>
        <article className="stat">
          <span>Assessments</span>
          <strong>{data.assessments.length}</strong>
        </article>
      </section>
      <div className="split">
        <section className="panel">
          <h2>Selected target</h2>
          {selectedTarget ? (
            <>
              <p>
                <strong>{selectedTarget.name}</strong>{" "}
                <StatusChip label={selectedTarget.authorization_status} />
              </p>
              <p className="muted wrap">{selectedTarget.scope.description}</p>
              <p className="mono muted">{selectedTarget.id}</p>
              <p>Expiry {formatTime(selectedTarget.authorization_expiry)}</p>
              <div className="chip-row">
                {selectedTarget.allowed_capabilities.map((item) => (
                  <StatusChip key={item} label={item} />
                ))}
              </div>
            </>
          ) : (
            <p className="muted">No target in this snapshot.</p>
          )}
        </section>
        <section className="panel">
          <h2>Recent cases</h2>
          <ul className="plain-list">
            {data.cases.slice(0, 5).map((item) => (
              <li key={item.id}>
                <Link to={`/investigations/${item.id}`}>{item.state}</Link>
                <span className="muted mono"> {formatTime(item.updated_at)}</span>
              </li>
            ))}
            {data.cases.length === 0 ? <li className="muted">No cases.</li> : null}
          </ul>
        </section>
        <section className="panel">
          <h2>Correlation</h2>
          <p>
            Risk score {data.risk?.score ?? "—"} · formula {data.risk?.formula ?? "unavailable"}
          </p>
          <p className="muted">Score is a documented point sum, not a probability of compromise.</p>
          <Link to="/graph">Open threat graph</Link>
        </section>
      </div>
      <section className="panel">
        <h2>Research status</h2>
        <p className="muted">
          Mode: {mode}. Independent public-dataset validation remains incomplete for Phases 11–13.
        </p>
        <ul className="phase-list">
          {phases.map((phase) => (
            <li key={phase.id}>
              <strong>{phase.title}</strong>
              <StatusChip label={phase.scientific} />
              <p>{phase.summary}</p>
            </li>
          ))}
        </ul>
        <Link to="/research">Open research observatory</Link>
      </section>
    </div>
  );
}
