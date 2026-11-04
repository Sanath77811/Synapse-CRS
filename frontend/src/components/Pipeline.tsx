const STAGES = [
  { id: "telemetry", label: "Telemetry" },
  { id: "features", label: "Features" },
  { id: "neural", label: "Neural" },
  { id: "symbolic", label: "Symbolic" },
  { id: "hybrid", label: "Hybrid" },
  { id: "hypothesis", label: "Hypothesis" },
  { id: "explain", label: "Explanation" },
];

export function Pipeline({
  active,
  onSelect,
}: {
  active: string;
  onSelect: (id: string) => void;
}) {
  return (
    <ol className="pipeline">
      {STAGES.map((stage, index) => (
        <li key={stage.id}>
          <button
            type="button"
            className={stage.id === active ? "pipe is-active" : "pipe"}
            onClick={() => onSelect(stage.id)}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            {stage.label}
          </button>
        </li>
      ))}
    </ol>
  );
}
