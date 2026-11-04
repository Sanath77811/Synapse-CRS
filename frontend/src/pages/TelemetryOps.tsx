import { useMemo, useState } from "react";
import type { AgentView } from "../api/types";
import { Field } from "../components/DetailPanel";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";

export function TelemetryOps() {
  const { data, selectedTarget, setSelectedTargetId, mode } = usePlatformContext();
  const [agent, setAgent] = useState<AgentView | null>(null);
  const events = useMemo(
    () => data.findings.flatMap((item) => item.supporting_events),
    [data.findings],
  );
  return (
    <div className="ops">
      <header className="ops-strip">
        <div>
          <p className="kicker">Telemetry operations</p>
          <h1>Enrollment vs receipt</h1>
        </div>
        <div className="ops-lamps">
          <span>targets {data.targets.length}</span>
          <span>agents {data.agents.length}</span>
          <span>supporting events {events.length}</span>
        </div>
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
      </header>
      <section className="ops-channels">
        {data.targets.map((item) => (
          <button
            type="button"
            key={item.id}
            className={item.id === selectedTarget?.id ? "channel is-on" : "channel"}
            onClick={() => setSelectedTargetId(item.id)}
          >
            <header>
              <b>{item.name}</b>
              <span>{item.authorization_status}</span>
            </header>
            <p className="mono wrap">{item.id}</p>
            <p className="dim">{item.scope.environment}</p>
          </button>
        ))}
      </section>
      <section className="ops-grid">
        <div>
          <h2>Agents {selectedTarget ? `· ${selectedTarget.name}` : ""}</h2>
          <div className="agent-matrix">
            {data.agents.map((item) => (
              <button
                type="button"
                key={item.id}
                className={agent?.id === item.id ? "agent-cell is-on" : "agent-cell"}
                onClick={() => setAgent(item)}
              >
                <span>{item.status}</span>
                <strong className="mono">{item.public_key_fingerprint}</strong>
                <em>gen {item.key_generation}</em>
              </button>
            ))}
            {data.agents.length === 0 ? <p className="dim">No enrolled agents.</p> : null}
          </div>
        </div>
        <div>
          <h2>Receipt ticker</h2>
          <p className="dim">
            Derived from finding.supporting_events — not a telemetry_events dump.
          </p>
          <ol className="ticker">
            {events.map((item) => (
              <li key={item.event_id}>
                <span className="mono">{formatTime(item.observed_at)}</span>
                <b>{item.event_type}</b>
                <span className="mono">{shortId(item.event_id)}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>
      {agent ? (
        <aside className="ops-inspect">
          <h2>Identity</h2>
          <Field label="Agent" value={agent.id} mono />
          <Field label="Fingerprint" value={agent.public_key_fingerprint} mono />
          <Field label="Public key" value={agent.public_key_hex} mono />
          <p className="dim">Public key is not a session token.</p>
        </aside>
      ) : null}
    </div>
  );
}
