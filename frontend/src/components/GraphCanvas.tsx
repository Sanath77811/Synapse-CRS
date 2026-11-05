import { memo, useMemo } from "react";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { layoutGraph } from "../lib/graphLayout";

const KindNode = memo(function KindNode({ data }: NodeProps) {
  const kind = String(data.kind ?? "event");
  const title = String(data.title ?? "");
  return (
    <div className={`gn gn-${kind}`}>
      <Handle type="target" position={Position.Left} />
      <span>{kind}</span>
      <strong>{title}</strong>
      <Handle type="source" position={Position.Right} />
    </div>
  );
});

const nodeTypes = { kind: KindNode };

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
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.35}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => onSelect(node.id)}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable
          defaultEdgeOptions={{
            type: "smoothstep",
            animated: false,
            style: { stroke: "rgba(125,211,252,0.45)", strokeWidth: 1.4 },
            labelStyle: { fill: "#8b98a8", fontSize: 10, fontFamily: "IBM Plex Mono, monospace" },
            labelBgStyle: { fill: "#0a1018", fillOpacity: 0.85 },
            labelBgPadding: [4, 6],
          }}
        >
          <Background gap={22} size={1} color="rgba(125, 211, 252, 0.07)" />
          <MiniMap
            className="graph-minimap"
            pannable
            zoomable
            maskColor="rgba(7,9,14,0.72)"
            nodeColor={(node) => {
              const kind = String(node.data.kind ?? "");
              if (kind === "target") {
                return "#a78bfa";
              }
              if (kind === "agent") {
                return "#5eead4";
              }
              if (kind === "finding") {
                return "#fbbf24";
              }
              return "#7dd3fc";
            }}
          />
          <Controls showInteractive={false} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
