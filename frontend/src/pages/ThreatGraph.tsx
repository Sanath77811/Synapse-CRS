import { useMemo, useState } from "react";
import type { Edge, Node } from "@xyflow/react";
import { GraphCanvas } from "../components/GraphCanvas";
import { DetailPanel, Field } from "../components/DetailPanel";
import { PageHeader } from "../components/PageHeader";
import { usePlatformContext } from "../context/PlatformContext";
import { shortId } from "../lib/format";

export function ThreatGraph() {
  const { data, selectedTarget, mode } = usePlatformContext();
  const [selected, setSelected] = useState<string | null>(null);
  const { nodes, edges } = useMemo(() => {
    const nextNodes: Node[] = [];
    const nextEdges: Edge[] = [];
    if (selectedTarget) {
      nextNodes.push({
        id: selectedTarget.id,
        data: { label: `target\n${selectedTarget.name}` },
        position: { x: 0, y: 0 },
        className: "g-target",
      });
    }
    for (const agent of data.agents) {
      nextNodes.push({
        id: agent.id,
        data: { label: `agent\n${shortId(agent.id)}` },
        position: { x: 0, y: 0 },
        className: "g-agent",
      });
      if (selectedTarget) {
        nextEdges.push({
          id: `t-a-${agent.id}`,
          source: selectedTarget.id,
          target: agent.id,
          label: "enrolled",
        });
      }
    }
    for (const finding of data.findings) {
      nextNodes.push({
        id: finding.id,
        data: { label: `finding\n${finding.finding_type}` },
        position: { x: 0, y: 0 },
        className: "g-finding",
      });
      if (selectedTarget) {
        nextEdges.push({
          id: `t-f-${finding.id}`,
          source: selectedTarget.id,
          target: finding.id,
          label: "finding",
        });
      }
      for (const event of finding.supporting_events) {
        if (!nextNodes.some((node) => node.id === event.event_id)) {
          nextNodes.push({
            id: event.event_id,
            data: { label: `event\n${event.event_type}` },
            position: { x: 0, y: 0 },
            className: "g-event",
          });
        }
        nextEdges.push({
          id: `f-e-${finding.id}-${event.event_id}`,
          source: finding.id,
          target: event.event_id,
          label: "supports",
        });
      }
    }
    for (const link of data.links) {
      for (const eventId of [link.left_event_id, link.right_event_id]) {
        if (!nextNodes.some((node) => node.id === eventId)) {
          nextNodes.push({
            id: eventId,
            data: { label: `event\n${shortId(eventId)}` },
            position: { x: 0, y: 0 },
            className: "g-event",
          });
        }
      }
      nextEdges.push({
        id: link.id,
        source: link.left_event_id,
        target: link.right_event_id,
        label: link.rule_id,
        className: "g-corr",
      });
    }
    return { nodes: nextNodes, edges: nextEdges };
  }, [data, selectedTarget]);

  const selectedNode = nodes.find((node) => node.id === selected);
  return (
    <div className="page with-panel">
      <div>
        <PageHeader
          kicker="Threat Graph"
          title="Evidence universe"
          summary="Edges are enrollment, finding support, or stored correlation links. No invented process trees. Zoom, pan, and select a node."
        />
        {mode === "demo" ? <p className="demo-flag">Synthetic relationship set</p> : null}
        {nodes.length === 0 ? (
          <p className="muted">No graphable entities in the current snapshot.</p>
        ) : (
          <GraphCanvas nodes={nodes} edges={edges} onSelect={setSelected} />
        )}
        <ul className="legend">
          <li><i className="g-target" /> Target</li>
          <li><i className="g-agent" /> Agent</li>
          <li><i className="g-finding" /> Finding</li>
          <li><i className="g-event" /> Event</li>
        </ul>
      </div>
      {selectedNode ? (
        <DetailPanel title="Node" onClose={() => setSelected(null)}>
          <Field label="Id" value={selectedNode.id} mono />
          <Field label="Label" value={String(selectedNode.data.label).replace("\n", " · ")} />
        </DetailPanel>
      ) : null}
    </div>
  );
}
