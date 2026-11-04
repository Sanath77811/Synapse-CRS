import { Link } from "react-router-dom";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";

export function SystemControl() {
  const { data, health, ready, mode, token } = usePlatformContext();
  return (
    <div className="page">
      <PageHeader
        kicker="System Control"
        title="Control plane"
        summary="Health probes are unauthenticated. Registry, audit, and enrollment reads require a bearer token. Frontend access control is not a security boundary."
        actions={<Link to="/session">Session</Link>}
      />
      <section className="stat-grid">
        <article className="stat">
          <span>Mode</span>
          <strong>{mode}</strong>
        </article>
        <article className="stat">
          <span>API</span>
          <strong>{health?.status ?? "down"}</strong>
        </article>
        <article className="stat">
          <span>Ready</span>
          <strong>{ready?.status ?? "unknown"}</strong>
        </article>
        <article className="stat">
          <span>Session</span>
          <strong>{token ? "token present" : "none"}</strong>
        </article>
      </section>
      <section className="panel">
        <h2>Audit chain</h2>
        {data.chain ? (
          <p>
            valid={String(data.chain.valid)} · events {data.chain.event_count} · head{" "}
            <span className="mono">{data.chain.head_hash ?? "—"}</span>
          </p>
        ) : (
          <p className="muted">Chain verification not loaded.</p>
        )}
        <DataTable
          rows={data.audit}
          empty="No audit events."
          columns={[
            { key: "seq", header: "Seq", render: (row) => String(row.sequence) },
            { key: "type", header: "Type", render: (row) => row.event_type },
            { key: "actor", header: "Actor", render: (row) => row.actor },
            { key: "at", header: "Time", render: (row) => formatTime(row.timestamp) },
            { key: "hash", header: "Hash", mono: true, render: (row) => shortId(row.event_hash) },
          ]}
        />
      </section>
      <section className="panel">
        <h2>Targets</h2>
        <DataTable
          rows={data.targets}
          empty="No targets."
          columns={[
            { key: "name", header: "Name", render: (row) => row.name },
            { key: "st", header: "Status", render: (row) => <StatusChip label={row.authorization_status} /> },
            { key: "el", header: "Eligible", render: (row) => String(row.eligible) },
          ]}
        />
      </section>
    </div>
  );
}
