import { Link } from "react-router-dom";

const STEPS = [
  { to: "/", label: "Command" },
  { to: "/telemetry", label: "Target" },
  { to: "/evidence", label: "Evidence" },
  { to: "/graph", label: "Graph" },
  { to: "/reasoning", label: "Reasoning" },
  { to: "/hypotheses", label: "Hypotheses" },
  { to: "/defence", label: "Defence" },
  { to: "/control", label: "Audit" },
];

export function Journey({ current }: { current?: string }) {
  return (
    <nav className="journey" aria-label="Investigation path">
      {STEPS.map((step, index) => (
        <span key={step.to}>
          {index > 0 ? <span className="hud-sep">→</span> : null}
          <Link className={current === step.to ? "is-now" : undefined} to={step.to}>
            {step.label}
          </Link>
        </span>
      ))}
    </nav>
  );
}
