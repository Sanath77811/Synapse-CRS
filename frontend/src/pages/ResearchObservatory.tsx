import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { RESEARCH_PHASES } from "../data/research";

export function ResearchObservatory() {
  return (
    <div className="page">
      <PageHeader
        kicker="Research Observatory"
        title="Methodology and limits"
        summary="Copied from repository research reports. Incomplete independent validation is shown as incomplete."
      />
      {RESEARCH_PHASES.map((phase) => (
        <article className="panel" key={phase.id}>
          <h2>{phase.title}</h2>
          <div className="chip-row">
            <StatusChip label={`engineering ${phase.engineering}`} />
            <StatusChip label={phase.scientific} />
            <StatusChip label={phase.independent ? "independent" : "not independent"} />
          </div>
          <p>{phase.summary}</p>
          <ul>
            {phase.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mono muted">{phase.command}</p>
        </article>
      ))}
    </div>
  );
}
