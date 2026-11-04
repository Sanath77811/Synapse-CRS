import { useMemo, useState } from "react";
import { DataTable } from "../components/DataTable";
import { DetailPanel, Field } from "../components/DetailPanel";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { Timeline } from "../components/Timeline";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";
import type { FindingView, SupportingEventView } from "../api/types";

export function EvidenceLab() {
  const { data, mode } = usePlatformContext();
  const [finding, setFinding] = useState<FindingView | null>(data.findings[0] ?? null);
  const events = useMemo(() => {
    const map = new Map<string, SupportingEventView>();
    for (const item of data.findings) {
      for (const event of item.supporting_events) {
        map.set(event.event_id, event);
      }
    }
    return [...map.values()];
  }, [data.findings]);
  const [event, setEvent] = useState<SupportingEventView | null>(null);
  return (
    <div className="page with-panel">
      <div>
        <PageHeader
          kicker="Evidence Lab"
          title="Forensic microscope"
          summary="Inspect findings, supporting event identifiers, missing evidence, and epistemic class. Inferred timeline items are never drawn as observed events."
        />
        <section className="panel">
          <h2>Findings</h2>
          <DataTable
            rows={data.findings}
            selectedId={finding?.id}
            onSelect={setFinding}
            empty="No findings. Run correlation against enrolled telemetry, or stay in demonstration mode."
            columns={[
              { key: "type", header: "Type", render: (row) => row.finding_type },
              { key: "sev", header: "Severity", render: (row) => <StatusChip label={row.severity} /> },
              { key: "ep", header: "Epistemic", render: (row) => row.epistemic_status },
              { key: "miss", header: "Missing", render: (row) => String(row.missing_evidence.length) },
            ]}
          />
        </section>
        <section className="panel">
          <h2>Event identifiers</h2>
          <DataTable
            rows={events.map((item) => ({ ...item, id: item.event_id }))}
            selectedId={event?.event_id}
            onSelect={(row) => setEvent(row)}
            empty="No event identifiers available."
            columns={[
              { key: "type", header: "Type", render: (row) => row.event_type },
              { key: "at", header: "Observed", render: (row) => formatTime(row.observed_at) },
              { key: "id", header: "Id", mono: true, render: (row) => shortId(row.event_id) },
            ]}
          />
        </section>
        {data.timeline ? (
          <section className="panel">
            <h2>Incident storyline</h2>
            <p className="muted">
              Observed, correlated, and inferred items use distinct treatments. Dataset:{" "}
              {data.timeline.dataset_label}
              {mode === "demo" ? " (synthetic lab)" : ""}.
            </p>
            <Timeline items={data.timeline.timeline} />
          </section>
        ) : null}
      </div>
      {finding ? (
        <DetailPanel title="Finding" onClose={() => setFinding(null)}>
          <Field label="Type" value={finding.finding_type} />
          <Field label="Epistemic" value={finding.epistemic_status} />
          <Field label="Confidence (engine score)" value={String(finding.confidence)} />
          <p>{finding.explanation}</p>
          <h3>Supporting events</h3>
          <ul>
            {finding.supporting_event_ids.map((id) => (
              <li key={id} className="mono wrap">
                {id}
              </li>
            ))}
          </ul>
          <h3>Missing</h3>
          <ul>
            {finding.missing_evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </DetailPanel>
      ) : event ? (
        <DetailPanel title="Event" onClose={() => setEvent(null)}>
          <Field label="Event id" value={event.event_id} mono />
          <Field label="Type" value={event.event_type} />
          <Field label="Observed" value={formatTime(event.observed_at)} mono />
          <Field label="Sequence" value={String(event.sequence)} />
        </DetailPanel>
      ) : null}
    </div>
  );
}
