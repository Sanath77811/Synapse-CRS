import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Field } from "../components/DetailPanel";
import { GraphCanvas } from "../components/GraphCanvas";
import { usePlatformContext } from "../context/PlatformContext";
import { graphFromSnapshot } from "../lib/graphFromSnapshot";

const KINDS = ["target", "agent", "finding", "event"] as const;

export function ThreatGraph() {
  const { data, selectedTarget, mode } = usePlatformContext();
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [kinds, setKinds] = useState<Set<string>>(() => new Set(KINDS));
  const { nodes, edges } = useMemo(
    () => graphFromSnapshot(data, selectedTarget),
    [data, selectedTarget],
  );

  const visible = useMemo(() => {
    const allowed = nodes.filter((node) => kinds.has(String(node.data.kind)));
    const ids = new Set(allowed.map((node) => node.id));
    const q = query.trim().toLowerCase();
    const focused = q
      ? new Set(
          allowed
            .filter(
              (node) =>
                node.id.toLowerCase().includes(q) ||
                String(node.data.title).toLowerCase().includes(q) ||
                String(node.data.kind).toLowerCase().includes(q),
            )
            .map((node) => node.id),
        )
      : null;
    return {
      nodes: allowed.map((node) => ({
        ...node,
        style: { ...node.style, opacity: focused && !focused.has(node.id) ? 0.22 : 1 },
      })),
      edges: edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
    };
  }, [edges, kinds, nodes, query]);

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
        <div className="kind-toggles" role="group" aria-label="Entity kinds">
          {KINDS.map((kind) => (
            <label key={kind}>
              <input
                type="checkbox"
                checked={kinds.has(kind)}
                onChange={() => {
                  setKinds((current) => {
                    const next = new Set(current);
                    if (next.has(kind)) {
                      next.delete(kind);
                    } else {
                      next.add(kind);
                    }
                    return next.size === 0 ? current : next;
                  });
                }}
              />
              {kind}
            </label>
          ))}
        </div>
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
      </div>
      {visible.nodes.length === 0 ? (
        <p className="dim pad">No graphable entities for the selected kinds.</p>
      ) : (
        <GraphCanvas nodes={visible.nodes} edges={visible.edges} onSelect={setSelected} />
      )}
      <ul className="float-legend">
        <li>
          <i className="gn-target" /> Target
        </li>
        <li>
          <i className="gn-agent" /> Agent
        </li>
        <li>
          <i className="gn-finding" /> Finding
        </li>
        <li>
          <i className="gn-event" /> Event
        </li>
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
          {String(selectedNode.data.kind) === "finding" ? (
            <p>
              <Link to={`/evidence?finding=${selectedNode.id}`}>Open in Evidence Lab</Link>
            </p>
          ) : (
            <p>
              <Link to="/evidence">Open Evidence Lab</Link>
            </p>
          )}
        </aside>
      ) : null}
    </div>
  );
}
