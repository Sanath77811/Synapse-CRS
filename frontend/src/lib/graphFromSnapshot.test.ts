import { describe, expect, it } from "vitest";
import { demoSnapshot } from "../data/demo";
import { graphFromSnapshot } from "./graphFromSnapshot";

describe("graphFromSnapshot", () => {
  it("builds only enrollment, finding, and correlation edges", () => {
    const snapshot = demoSnapshot();
    const { nodes, edges } = graphFromSnapshot(snapshot, snapshot.targets[0]);
    const kinds = new Set(nodes.map((node) => String(node.data.kind)));
    expect(kinds.has("target")).toBe(true);
    expect(kinds.has("agent")).toBe(true);
    expect(kinds.has("finding")).toBe(true);
    expect(kinds.has("event")).toBe(true);
    expect(edges.some((edge) => edge.label === "enrolled")).toBe(true);
    expect(edges.some((edge) => edge.label === "supports")).toBe(true);
    expect(nodes.every((node) => node.position.x === 0 && node.position.y === 0)).toBe(true);
  });

  it("does not invent nodes when the snapshot is empty", () => {
    const { nodes, edges } = graphFromSnapshot(
      {
        targets: [],
        cases: [],
        agents: [],
        findings: [],
        links: [],
        risk: null,
        assessments: [],
        timeline: null,
        audit: [],
        chain: null,
      },
      null,
    );
    expect(nodes).toEqual([]);
    expect(edges).toEqual([]);
  });
});
