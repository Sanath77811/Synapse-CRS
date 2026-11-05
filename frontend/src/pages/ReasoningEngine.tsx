import { Link } from "react-router-dom";
import { useState } from "react";
import { Field } from "../components/DetailPanel";
import { Journey } from "../components/Journey";
import { usePlatformContext } from "../context/PlatformContext";
import { explainSelectedHypothesis } from "../lib/h4Explain";

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
        <p className="dim pad">No assessment. Live runs require admin POST /reasoning/assessments.</p>
      </div>
    );
  }
  const selected = assessment.hypotheses.find(
    (item) => item.hypothesis_id === assessment.selected_hypothesis,
  );
  const copy: Record<string, string> = {
    telemetry: `Observed event ids in this assessment: ${assessment.evidence_event_ids.join(", ") || "none"}. Ingest is signed POST; this page does not list a telemetry dump.`,
    features: `coverage=${assessment.quality.telemetry_coverage} identity=${assessment.quality.identity_verification} lifecycle=${assessment.quality.lifecycle_completeness} reconstruction=${assessment.quality.reconstruction_completeness}. ${assessment.quality.notes.join(" ")}`,
    neural: `${assessment.neural.model_id} unusualness=${assessment.neural.unusualness_score} threshold=${assessment.neural.threshold} unusual=${String(assessment.neural.unusual)}. Unusualness is not a probability. ${assessment.neural.limitations}`,
    symbolic: `Rule ids: ${assessment.explanation.rule_ids.join(", ") || "none"}. ${assessment.explanation.symbolic}`,
    hybrid: explainSelectedHypothesis(assessment),
    hypothesis: assessment.hypotheses
      .map((item) => `${item.hypothesis_id} ${item.status} support=${item.support}`)
      .join(" · "),
    explain: `Observed: ${assessment.explanation.observed} Correlated: ${assessment.explanation.correlated} Inferred via hybrid selection, not direct observation of intent. Missing: ${assessment.explanation.missing}`,
  };
  return (
    <div className="theatre">
      <aside className="theatre-svg">
        <p className="kicker">Reasoning theatre</p>
        <h1>Neuro-symbolic stack</h1>
        <Journey current="/reasoning" />
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
            <g
              key={item.id}
              className={stage === item.id ? "stack-node is-on" : "stack-node"}
              onClick={() => setStage(item.id)}
            >
              <circle cx="40" cy={item.y} r="11" />
              <text x="62" y={item.y + 4}>
                {String(index + 1).padStart(2, "0")} {item.label}
              </text>
            </g>
          ))}
        </svg>
        <p className="dim">Architecture diagram. Numbers come from the stored assessment, not a live GPU trace.</p>
      </aside>
      <section className="theatre-readout">
        <header>
          <h2>{stage}</h2>
          <span className="mono">
            {assessment.engine_version} · {assessment.dataset_label}
          </span>
        </header>
        <p className="readout-body">{copy[stage]}</p>
        <Field label="Selected" value={assessment.selected_hypothesis} />
        <Field label="Engine score" value={String(assessment.confidence)} />
        <p className="dim">{assessment.uncertainty}</p>
        {selected ? <p className="dim">{selected.rationale}</p> : null}
        <ul className="lim">
          {assessment.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p>
          <Link to="/hypotheses">Compare hypotheses</Link>
          {" · "}
          <Link to="/defence">Policy verification</Link>
        </p>
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
