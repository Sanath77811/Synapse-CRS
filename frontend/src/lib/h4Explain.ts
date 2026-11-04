import type { ReasoningAssessmentView } from "../api/types";

/** Copy derived from the stored assessment. Does not invent a detection claim. */
export function explainSelectedHypothesis(assessment: ReasoningAssessmentView): string {
  const selected = assessment.hypotheses.find(
    (item) => item.hypothesis_id === assessment.selected_hypothesis,
  );
  const quality = assessment.quality;
  const parts = [
    selected?.rationale,
    `Selected ${assessment.selected_hypothesis}. Support score ${assessment.confidence} is an engine score, not a probability or detection rate.`,
    `Quality: coverage=${quality.telemetry_coverage} identity=${quality.identity_verification} lifecycle=${quality.lifecycle_completeness} reconstruction=${quality.reconstruction_completeness}.`,
  ];
  if (assessment.selected_hypothesis === "H4_insufficient_evidence") {
    parts.push(
      "H4 wins when reconstruction is sparse or tied with a stronger claim. Incomplete evidence is not treated as malice.",
    );
  }
  if (assessment.missing_evidence.length > 0) {
    parts.push(`Missing: ${assessment.missing_evidence.join(", ")}.`);
  }
  return parts.filter(Boolean).join(" ");
}
