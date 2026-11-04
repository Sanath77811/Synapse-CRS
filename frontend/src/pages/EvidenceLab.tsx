import { useState } from "react";
import type { FindingView, SupportingEventView } from "../api/types";
import { Field } from "../components/DetailPanel";
import { Timeline } from "../components/Timeline";
import { usePlatformContext } from "../context/PlatformContext";
import { formatTime, shortId } from "../lib/format";

export function EvidenceLab() {
  const { data, mode } = usePlatformContext();
  const [query, setQuery] = useState("");
  const [finding, setFinding] = useState<FindingView | null>(data.findings[0] ?? null);
  const [event, setEvent] = useState<SupportingEventView | null>(null);
  const q = query.trim().toLowerCase();
  const findings = data.findings.filter((item) => {
    if (!q) {
      return true;
    }
    return (
      item.finding_type.toLowerCase().includes(q) ||
      item.explanation.toLowerCase().includes(q) ||
      item.supporting_events.some((row) => row.event_type.toLowerCase().includes(q))
    );
  });
  return (
    <div className="forensic">
      <aside className="fx-tree">
        <h2>Explorer</h2>
        <p className="dim">Findings → supporting events. No invented process trees.</p>
        <input
          value={query}
          onChange={(change) => setQuery(change.target.value)}
          placeholder="filter evidence…"
          aria-label="Filter evidence"
        />
        <ul className="tree">
          {findings.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={finding?.id === item.id ? "tree-btn is-on" : "tree-btn"}
                onClick={() => {
                  setFinding(item);
                  setEvent(null);
                }}
              >
                {item.finding_type.replaceAll("_", " ")}
              </button>
              <ul>
                {item.supporting_events.map((row) => (
                  <li key={row.event_id}>
                    <button
                      type="button"
                      className={event?.event_id === row.event_id ? "tree-btn is-on" : "tree-btn"}
                      onClick={() => setEvent(row)}
                    >
                      {row.event_type}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </aside>
      <section className="fx-canvas">
        <header className="fx-head">
          <div>
            <p className="kicker">Evidence Lab</p>
            <h1>Forensic canvas</h1>
          </div>
          {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
        </header>
        <div className="relation-map">
          {finding ? (
            <>
              <article className="rel rel-find">{finding.finding_type.replaceAll("_", " ")}</article>
              <div className="rel-links">
                {finding.supporting_events.map((row) => (
                  <button
                    type="button"
                    key={row.event_id}
                    className="rel rel-ev"
                    onClick={() => setEvent(row)}
                  >
                    {row.event_type}
                    <span className="mono">{shortId(row.event_id)}</span>
                  </button>
                ))}
              </div>
              {finding.missing_evidence.length > 0 ? (
                <article className="rel rel-miss">
                  missing: {finding.missing_evidence.join(" · ")}
                </article>
              ) : null}
            </>
          ) : (
            <p className="dim">Select a finding.</p>
          )}
        </div>
      </section>
      <aside className="fx-inspect">
        <h2>Inspector</h2>
        {event ? (
          <>
            <Field label="Event" value={event.event_id} mono />
            <Field label="Type" value={event.event_type} />
            <Field label="Observed" value={formatTime(event.observed_at)} mono />
            <Field label="Sequence" value={String(event.sequence)} />
          </>
        ) : finding ? (
          <>
            <Field label="Finding" value={finding.finding_type} />
            <Field label="Epistemic" value={finding.epistemic_status} />
            <Field label="Engine score" value={String(finding.confidence)} />
            <p>{finding.explanation}</p>
            <h3>Provenance</h3>
            <ul>
              {finding.supporting_event_ids.map((id) => (
                <li key={id} className="mono wrap">
                  {id}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="dim">Nothing selected.</p>
        )}
      </aside>
      <footer className="fx-tape">
        <h2>Storyline</h2>
        {data.timeline ? (
          <Timeline items={data.timeline.timeline} />
        ) : (
          <p className="dim">No reconstruction timeline in this snapshot.</p>
        )}
      </footer>
    </div>
  );
}
