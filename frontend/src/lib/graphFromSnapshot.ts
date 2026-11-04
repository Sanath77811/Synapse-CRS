import type { Edge, Node } from "@xyflow/react";
import type { PlatformSnapshot, TargetView } from "../api/types";
import { shortId } from "./format";

export function graphFromSnapshot(
  data: PlatformSnapshot,
  selectedTarget: TargetView | null,
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const add = (id: string, kind: string, title: string) => {
    if (!nodes.some((node) => node.id === id)) {
      nodes.push({ id, type: "kind", data: { kind, title }, position: { x: 0, y: 0 } });
    }
  };
  if (selectedTarget) {
    add(selectedTarget.id, "target", selectedTarget.name);
  }
  for (const agent of data.agents) {
    add(agent.id, "agent", shortId(agent.id));
    if (selectedTarget) {
      edges.push({ id: `t-a-${agent.id}`, source: selectedTarget.id, target: agent.id, label: "enrolled" });
    }
  }
  for (const finding of data.findings) {
    add(finding.id, "finding", finding.finding_type.replaceAll("_", " "));
    if (selectedTarget) {
      edges.push({ id: `t-f-${finding.id}`, source: selectedTarget.id, target: finding.id, label: "finding" });
    }
    for (const event of finding.supporting_events) {
      add(event.event_id, "event", event.event_type);
      edges.push({
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
    edges.push({
      id: link.id,
      source: link.left_event_id,
      target: link.right_event_id,
      label: link.rule_id,
    });
  }
  return { nodes, edges };
}
