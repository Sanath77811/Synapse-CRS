import { describe, expect, it } from "vitest";
import { RESEARCH_PHASES } from "./research";

describe("research catalog", () => {
  it("does not mark independent validation complete", () => {
    expect(RESEARCH_PHASES.every((item) => item.independent === false)).toBe(true);
    expect(RESEARCH_PHASES.some((item) => item.id === "phase-13" && item.scientific === "not_completed")).toBe(
      true,
    );
  });
});
