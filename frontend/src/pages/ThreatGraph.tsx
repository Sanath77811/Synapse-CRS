import { useMemo, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { Field } from "../components/DetailPanel";
import { GraphCanvas } from "../components/GraphCanvas";
import { usePlatformContext } from "../context/PlatformContext";
import { shortId } from "../lib/format";

export function ThreatGraph() {
  const { data, selectedTarget, mode } = usePlatformContext();
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const { nodes, edges } = useMemo(() => {
    const nextNodes: Node[] = [];
    const nextEdges: Edge[] = [];
    const add = (id: string, kind: string, title: string) => {
      if (!nextNodes.some((node) => node.id === id)) {
        nextNodes.push({
          id,
          type: "kind",
          data: { kind, title },
          position: { x: 0, y: 0 },
        });
      }
    };
    if (selectedTarget) {
      add(selectedTarget.id, "target", selectedTarget.name);
    }
    for (const agent of data.agents) {
      add(agent.id, "agent", shortId(agent.id));
      if (selectedTarget) {
        nextEdges.push({ id: `t-a-${agent.id}`, source: selectedTarget.id, target: agent.id, label: "enrolled" });
      }
    }
    for (const finding of data.findings) {
      add(finding.id, "finding", finding.finding_type.replaceAll("_", " "));
      if (selectedTarget) {
        nextEdges.push({ id: `t-f-${finding.id}`, source: selectedTarget.id, target: finding.id, label: "finding" });
      }
      for (const event of finding.supporting_events) {
        add(event.event_id, "event", event.event_type);
        nextEdges.push({
          id: `f-e-${finding.id}-${event.event_id}`,
          source: finding.id,
          target: event.event_id,
          label: "supports",
        });
      }
    }
    for (const link of data.links) {
      add(link.left_event_id, "event", shortId(link.left_event_id));
      add(link.right_event_id, "event", shortId(link.right_event_id));
      nextEdges.push({
        id: link.id,
        source: link.left_event_id,
        target: link.right_event_id,
        label: link.rule_id,
      });
    }
    return { nodes: nextNodes, edges: nextEdges };
  }, [data, selectedTarget]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return nodes;
    }
    const hit = new Set(
      nodes.filter((node) => JSON.stringify(node.data).toLowerCase().includes(q) || node.id.includes(q)).map((n) => n.id),
    );
    return nodes.map((node) => ({
      ...node,
      style: { ...node.style, opacity: hit.has(node.id) ? 1 : 0.22 },
    }));
  }, [nodes, query]);

  const selectedNode = nodes.find((node) => node.id === selected);
  return (
    <div className="graph-stage">
      <div className="float-bar">
        <div>
          <p className="kicker">Threat Graph</p>
          <h1>Investigation canvas</h1>
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="focus node…"
          aria-label="Focus nodes"
        />
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
      </div>
      {nodes.length === 0 ? (
        <p className="dim pad">No graphable entities.</p>
      ) : (
        <GraphCanvas nodes={filtered} edges={edges} onSelect={setSelected} />
      )}
      <ul className="float-legend">
        <li><i className="gn-target" /> Target</li>
        <li><i className="gn-agent" /> Agent</li>
        <li><i className="gn-finding" /> Finding</li>
        <li><i className="gn-event" /> Event</li>
      </ul>
      {selectedNode ? (
        <aside className="float-inspect">
          <header>
            <h2>Node</h2>
            <button type="button" className="ghost" onClick={() => setSelected(null)}>
              Close
            </button>
          </header>
          <Field label="Id" value={selectedNode.id} mono />
          <Field label="Kind" value={String(selectedNode.data.kind)} />
          <Field label="Title" value={String(selectedNode.data.title)} />
          <p className="dim">Edges are enrollment, finding support, or stored correlation only.</p>
        </aside>
      ) : null}
    </div>
  );
}
