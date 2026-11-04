import { useState } from "react";
import { usePlatformContext } from "../context/PlatformContext";

const STAGES = [
  { id: "telemetry", y: 36, label: "Telemetry" },
  { id: "features", y: 108, label: "Features" },
  { id: "neural", y: 180, label: "Neural" },
  { id: "symbolic", y: 252, label: "Symbolic" },
  { id: "hybrid", y: 324, label: "Hybrid" },
  { id: "hypothesis", y: 396, label: "Hypothesis" },
  { id: "explain", y: 468, label: "Explanation" },
];

export function ReasoningEngine() {
  const { data, mode } = usePlatformContext();
  const assessment = data.assessments[0];
  const [stage, setStage] = useState("hybrid");
  if (!assessment) {
    return (
      <div className="theatre empty-theatre">
        <p className="dim">No assessment. Live runs require admin POST /reasoning/assessments.</p>
      </div>
    );
  }
  const copy: Record<string, string> = {
    telemetry: `Evidence event ids: ${assessment.evidence_event_ids.join(", ") || "none"}`,
    features: `coverage=${assessment.quality.telemetry_coverage} identity=${assessment.quality.identity_verification} lifecycle=${assessment.quality.lifecycle_completeness}`,
    neural: `${assessment.neural.model_id} unusualness=${assessment.neural.unusualness_score} threshold=${assessment.neural.threshold}. ${assessment.neural.limitations}`,
    symbolic: `Rules: ${assessment.explanation.rule_ids.join(", ") || "none"}`,
    hybrid: `${assessment.explanation.summary} Selected ${assessment.selected_hypothesis}.`,
    hypothesis: assessment.hypotheses.map((item) => `${item.hypothesis_id} (${item.status})`).join(" · "),
    explain: `${assessment.explanation.observed} Missing: ${assessment.explanation.missing}`,
  };
  return (
    <div className="theatre">
      <aside className="theatre-svg">
        <p className="kicker">Reasoning theatre</p>
        <h1>Neuro-symbolic stack</h1>
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
        <svg viewBox="0 0 280 520" className="stack-svg" role="img" aria-label="Reasoning stages">
          {STAGES.slice(0, -1).map((item, index) => (
            <line
              key={item.id}
              x1="40"
              y1={item.y + 18}
              x2="40"
              y2={STAGES[index + 1].y - 8}
              className="stack-wire"
            />
          ))}
          {STAGES.map((item, index) => (
            <g key={item.id} className={stage === item.id ? "stack-node is-on" : "stack-node"} onClick={() => setStage(item.id)}>
              <circle cx="40" cy={item.y} r="11" />
              <text x="62" y={item.y + 4}>
                {String(index + 1).padStart(2, "0")} {item.label}
              </text>
            </g>
          ))}
        </svg>
        <p className="dim">Illustration of architecture. Values below are from the assessment payload, not a live GPU trace.</p>
      </aside>
      <section className="theatre-readout">
        <header>
          <h2>{stage}</h2>
          <span className="mono">
            {assessment.engine_version} · {assessment.dataset_label}
          </span>
        </header>
        <p className="readout-body">{copy[stage]}</p>
        <p className="dim">{assessment.uncertainty}</p>
        <ul className="lim">
          {assessment.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {assessment.counterfactual ? (
          <div className="ablation">
            <h3>Feature ablation</h3>
            <p>{assessment.counterfactual.description}</p>
            <p>
              {assessment.counterfactual.baseline_hypothesis} → {assessment.counterfactual.result_hypothesis}
            </p>
            <p className="dim">{assessment.counterfactual.limitations}</p>
          </div>
        ) : (
          <p className="dim">No counterfactual on this assessment.</p>
        )}
      </section>
    </div>
  );
}
