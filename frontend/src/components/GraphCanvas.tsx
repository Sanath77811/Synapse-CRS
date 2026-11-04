import { useMemo } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { layoutGraph } from "../lib/graphLayout";

export function GraphCanvas({
  nodes,
  edges,
  onSelect,
}: {
  nodes: Node[];
  edges: Edge[];
  onSelect: (id: string) => void;
}) {
  const laidOut = useMemo(() => layoutGraph(nodes, edges), [nodes, edges]);
  return (
    <div className="graph-shell">
      <ReactFlowProvider>
      <ReactFlow
        nodes={laidOut.nodes}
        edges={laidOut.edges}
        fitView
        minZoom={0.4}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => onSelect(node.id)}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
      >
        <Background gap={18} size={1} color="rgba(125, 211, 252, 0.08)" />
        <MiniMap pannable zoomable />
        <Controls showInteractive={false} />
      </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
