import { describe, expect, it } from "vitest";
import { demoSnapshot } from "../data/demo";
import { explainSelectedHypothesis } from "./h4Explain";

describe("explainSelectedHypothesis", () => {
  it("states that support is not a probability", () => {
    const assessment = demoSnapshot().assessments[0];
    const text = explainSelectedHypothesis(assessment);
    expect(text).toContain("not a probability");
    expect(text).toContain(assessment.selected_hypothesis);
  });
});
