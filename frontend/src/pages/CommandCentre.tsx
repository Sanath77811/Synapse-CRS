import { Link } from "react-router-dom";
import { IntelligenceCore } from "../components/IntelligenceCore";
import { usePlatformContext } from "../context/PlatformContext";
import { RESEARCH_PHASES } from "../data/research";
import { formatTime } from "../lib/format";

export function CommandCentre() {
  const { data, health, ready, selectedTarget, error, state, mode, source } = usePlatformContext();
  const latestFinding = data.findings[0];
  const latestCase = data.cases[0];
  return (
    <div className="command">
      <aside className="zone zone-health">
        <h2>Plant</h2>
        <ol className="meters">
          <li>
            <span>Control plane</span>
            <b>{health?.status ?? "offline"}</b>
            <i style={{ width: health?.status === "ok" ? "82%" : "18%" }} />
          </li>
          <li>
            <span>Store</span>
            <b>{ready?.status ?? "unknown"}</b>
            <i style={{ width: ready?.status === "ready" ? "76%" : "22%" }} />
          </li>
          <li>
            <span>Enrolled agents</span>
            <b>{data.agents.length}</b>
            <i style={{ width: `${Math.min(100, data.agents.length * 34)}%` }} />
          </li>
          <li>
            <span>Findings</span>
            <b>{data.findings.length}</b>
            <i style={{ width: `${Math.min(100, 20 + data.findings.length * 20)}%` }} />
          </li>
        </ol>
        <p className="dim note">Enrollment is not receipt of telemetry. Ingest is signed POST only.</p>
      </aside>
      <section className="zone zone-core">
        {error ? <p className="error-banner">{error}</p> : null}
        {state === "loading" ? <p className="dim">Assembling snapshot…</p> : null}
        <IntelligenceCore />
        <p className="core-caption">
          Spatial map of registered targets, findings and assessments in this snapshot.
          Source={source}. {mode === "demo" ? "Synthetic lab geometry." : ""} Not a live packet radar.
        </p>
      </section>
      <aside className="zone zone-side">
        <h2>Target lock</h2>
        {selectedTarget ? (
          <div className="lock-card">
            <strong>{selectedTarget.name}</strong>
            <span className="mono wrap">{selectedTarget.id}</span>
            <span>{selectedTarget.authorization_status}</span>
            <span className="dim">{selectedTarget.scope.environment}</span>
          </div>
        ) : (
          <p className="dim">No target.</p>
        )}
        <h2>Latest finding</h2>
        {latestFinding ? (
          <Link className="ribbon" to="/evidence">
            <b>{latestFinding.finding_type.replaceAll("_", " ")}</b>
            <span>{latestFinding.epistemic_status}</span>
            <span className="dim">{latestFinding.explanation}</span>
          </Link>
        ) : (
          <p className="dim">None.</p>
        )}
        <h2>Research honesty</h2>
        <ul className="stamp-list">
          {RESEARCH_PHASES.map((phase) => (
            <li key={phase.id}>
              <Link to={`/research/${phase.id}`}>{phase.id}</Link>
              <span>{phase.scientific}</span>
            </li>
          ))}
        </ul>
        <Link to="/research">Observatory →</Link>
      </aside>
      <footer className="zone zone-tape">
        <h2>Activity tape</h2>
        <div className="tape">
          {data.audit.slice(0, 8).map((item) => (
            <div key={item.id} className="tape-cell">
              <span className="mono">{formatTime(item.timestamp)}</span>
              <b>{item.event_type}</b>
              <span className="dim">{item.actor}</span>
            </div>
          ))}
          {latestCase ? (
            <Link className="tape-cell" to={`/investigations/${latestCase.id}`}>
              <span className="mono">{formatTime(latestCase.updated_at)}</span>
              <b>case {latestCase.state}</b>
              <span className="dim">open studio</span>
            </Link>
          ) : null}
          {data.audit.length === 0 && !latestCase ? <p className="dim">No audit or case activity.</p> : null}
        </div>
      </footer>
    </div>
  );
}
