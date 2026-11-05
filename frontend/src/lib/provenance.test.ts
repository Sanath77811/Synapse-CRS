import { describe, expect, it } from "vitest";
import { provenanceFlag } from "./provenance";

describe("provenanceFlag", () => {
  it("labels synthetic_lab live assessments as laboratory envelopes", () => {
    const flag = provenanceFlag("live", "live", false, "synthetic_lab");
    expect(flag.kind).toBe("laboratory");
    expect(flag.note).toContain("Not /proc");
  });

  it("does not call a live failure demo", () => {
    const flag = provenanceFlag("live", "unavailable", false, null);
    expect(flag.kind).toBe("unavailable");
    expect(flag.note).toContain("not substituted");
  });
});
