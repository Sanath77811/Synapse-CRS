import { useMemo, useState } from "react";
import { DataTable } from "../components/DataTable";
import { DetailPanel, Field } from "../components/DetailPanel";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";
import type { AgentView, SupportingEventView } from "../api/types";

export function TelemetryOps() {
  const { data, selectedTarget, mode } = usePlatformContext();
  const [agent, setAgent] = useState<AgentView | null>(null);
  const events = useMemo(() => {
    const rows: SupportingEventView[] = [];
    for (const finding of data.findings) {
      rows.push(...finding.supporting_events);
    }
    return rows;
  }, [data.findings]);
  return (
    <div className="page with-panel">
      <div>
        <PageHeader
          kicker="Telemetry Operations"
          title="Enrollment versus receipt"
          summary="Agents listed here are enrolled identities. Event rows are supporting observations attached to findings. There is no public list-telemetry endpoint; ingest is signature-authenticated POST only."
        />
        <section className="panel">
          <h2>Target inventory</h2>
          <DataTable
            rows={data.targets}
            empty="No registered targets."
            columns={[
              { key: "name", header: "Name", render: (row) => row.name },
              { key: "status", header: "Authorization", render: (row) => <StatusChip label={row.authorization_status} /> },
              { key: "scope", header: "Scope", render: (row) => row.scope.environment },
              { key: "id", header: "Id", mono: true, render: (row) => shortId(row.id) },
            ]}
          />
        </section>
        <section className="panel">
          <h2>Enrolled agents {selectedTarget ? `· ${selectedTarget.name}` : ""}</h2>
          <DataTable
            rows={data.agents}
            selectedId={agent?.id}
            onSelect={setAgent}
            empty="No enrolled agents for this target."
            columns={[
              { key: "status", header: "Status", render: (row) => <StatusChip label={row.status} /> },
              { key: "fp", header: "Fingerprint", mono: true, render: (row) => row.public_key_fingerprint },
              { key: "gen", header: "Gen", render: (row) => String(row.key_generation) },
              { key: "enrolled", header: "Enrolled", render: (row) => formatTime(row.enrolled_at) },
            ]}
          />
        </section>
        <section className="panel">
          <h2>Supporting observations on findings</h2>
          <p className="muted">
            {mode === "demo"
              ? "Synthetic supporting events from the demonstration finding."
              : "Derived from finding.supporting_events, not a raw telemetry dump."}
          </p>
          <DataTable
            rows={events.map((item) => ({ ...item, id: item.event_id }))}
            empty="No supporting events on current findings."
            columns={[
              { key: "type", header: "Type", render: (row) => row.event_type },
              { key: "seq", header: "Seq", render: (row) => String(row.sequence) },
              { key: "at", header: "Observed", render: (row) => formatTime(row.observed_at) },
              { key: "id", header: "Event", mono: true, render: (row) => shortId(row.event_id) },
            ]}
          />
        </section>
      </div>
      {agent ? (
        <DetailPanel title="Agent identity" onClose={() => setAgent(null)}>
          <Field label="Agent id" value={agent.id} mono />
          <Field label="Target" value={agent.target_id} mono />
          <Field label="Fingerprint" value={agent.public_key_fingerprint} mono />
          <Field label="Public key" value={agent.public_key_hex} mono />
          <Field label="Status" value={agent.status} />
          <p className="muted">The public key is not a private key and is not a session token.</p>
        </DetailPanel>
      ) : null}
    </div>
  );
}
