import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { Pipeline } from "../components/Pipeline";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";

export function ReasoningEngine() {
  const { data, mode } = usePlatformContext();
  const assessment = data.assessments[0];
  const [stage, setStage] = useState("hybrid");
  if (!assessment) {
    return (
      <div className="page">
        <PageHeader
          kicker="Reasoning Engine"
          title="Reasoning theatre"
          summary="No assessment is present. Live assessments are created by POST /api/v1/targets/{id}/reasoning/assessments (admin)."
        />
      </div>
    );
  }
  const copy: Record<string, string> = {
    telemetry: `Evidence event ids: ${assessment.evidence_event_ids.join(", ") || "none"}`,
    features: `Quality coverage=${assessment.quality.telemetry_coverage} identity=${assessment.quality.identity_verification} lifecycle=${assessment.quality.lifecycle_completeness}`,
    neural: `${assessment.neural.model_id} unusualness=${assessment.neural.unusualness_score} threshold=${assessment.neural.threshold}. ${assessment.neural.limitations}`,
    symbolic: `Rules in explanation: ${assessment.explanation.rule_ids.join(", ") || "none"}`,
    hybrid: `${assessment.explanation.summary} Selected ${assessment.selected_hypothesis}.`,
    hypothesis: assessment.hypotheses.map((item) => `${item.hypothesis_id} (${item.status})`).join(" · "),
    explain: `${assessment.explanation.observed} ${assessment.explanation.missing}`,
  };
  return (
    <div className="page">
      <PageHeader
        kicker="Reasoning Engine"
        title="Reasoning theatre"
        summary="Inspect each pipeline stage. Scores are engine outputs, not calibrated probabilities. Dataset label is shown rather than implied production accuracy."
      />
      {mode === "demo" ? <p className="demo-flag">Synthetic lab assessment</p> : null}
      <p>
        Engine {assessment.engine_version} · dataset {assessment.dataset_label} ·{" "}
        <StatusChip label={assessment.severity} />
      </p>
      <Pipeline active={stage} onSelect={setStage} />
      <section className="panel">
        <h2>{stage}</h2>
        <p>{copy[stage]}</p>
        <p className="muted">{assessment.uncertainty}</p>
        <ul>
          {assessment.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
      {assessment.counterfactual ? (
        <section className="panel">
          <h2>What-if (feature ablation)</h2>
          <p>{assessment.counterfactual.description}</p>
          <p>
            {assessment.counterfactual.baseline_hypothesis} → {assessment.counterfactual.result_hypothesis}
          </p>
          <p className="muted">{assessment.counterfactual.limitations}</p>
        </section>
      ) : (
        <p className="muted">No counterfactual payload on this assessment.</p>
      )}
    </div>
  );
}
