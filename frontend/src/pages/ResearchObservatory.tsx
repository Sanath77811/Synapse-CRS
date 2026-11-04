import { RESEARCH_PHASES } from "../data/research";

export function ResearchObservatory() {
  return (
    <div className="lab">
      <header>
        <p className="kicker">Research observatory</p>
        <h1>Lab notebooks</h1>
        <p className="dim">Copied from repository reports. Incomplete independent validation is not restyled as success.</p>
      </header>
      <div className="notebooks">
        {RESEARCH_PHASES.map((phase) => (
          <article key={phase.id} className="note">
            <header>
              <em>{phase.id}</em>
              <span className={`seal seal-${phase.scientific}`}>{phase.scientific}</span>
            </header>
            <h2>{phase.title}</h2>
            <p>{phase.summary}</p>
            <ul>
              {phase.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mono dim">{phase.command}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
