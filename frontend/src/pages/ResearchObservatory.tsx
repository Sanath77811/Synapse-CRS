import { Link, useParams } from "react-router-dom";
import { RESEARCH_PHASES } from "../data/research";

export function ResearchObservatory() {
  const { phaseId } = useParams();
  const selected = RESEARCH_PHASES.find((phase) => phase.id === phaseId) ?? null;
  return (
    <div className="lab">
      <header>
        <p className="kicker">Research observatory</p>
        <h1>{selected ? selected.title : "Lab notebooks"}</h1>
        <p className="dim">
          Copied from repository reports. Incomplete independent validation is not restyled as
          success.
        </p>
      </header>
      {selected ? (
        <article className="note note-open">
          <header>
            <em>{selected.id}</em>
            <span className={`seal seal-${selected.scientific}`}>{selected.scientific}</span>
          </header>
          <p>
            Engineering: {selected.engineering}. Independent dataset evaluation:{" "}
            {selected.independent ? "claimed complete" : "not completed"}.
          </p>
          <p>{selected.summary}</p>
          <h2>Limitations</h2>
          <ul>
            {selected.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mono dim">{selected.command}</p>
          <Link to="/research">All phases</Link>
        </article>
      ) : (
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
              <Link to={`/research/${phase.id}`}>Open notebook</Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
