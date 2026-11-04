import { useState } from "react";
import { Link } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";

export function HypothesisArena() {
  const { data, mode } = usePlatformContext();
  const assessment = data.assessments[0];
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(1);
  if (!assessment) {
    return (
      <div className="arena">
        <p className="dim pad">No hypotheses until an assessment exists.</p>
      </div>
    );
  }
  const a = assessment.hypotheses[left];
  const b = assessment.hypotheses[right];
  return (
    <div className="arena">
      <header className="arena-head">
        <div>
          <p className="kicker">Hypothesis arena</p>
          <h1>Competing explanations</h1>
          <p className="dim">Support scores are engine values, not probabilities. Selected is not a verdict.</p>
        </div>
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
      </header>
      <div className="duel">
        {[a, b].map((item, index) => (
          <section key={item.hypothesis_id} className="brief">
            <label>
              {index === 0 ? "Left" : "Right"}
              <select
                value={index === 0 ? left : right}
                onChange={(event) =>
                  index === 0 ? setLeft(Number(event.target.value)) : setRight(Number(event.target.value))
                }
              >
                {assessment.hypotheses.map((option, optionIndex) => (
                  <option key={option.hypothesis_id} value={optionIndex}>
                    {option.hypothesis_id}
                  </option>
                ))}
              </select>
            </label>
            <h2>{item.hypothesis_id}</h2>
            <p className="support">
              {item.status} · {item.support} support score
            </p>
            <p>{item.rationale}</p>
            <h3>Supports</h3>
            <ul>
              {item.supporting_event_ids.map((id) => (
                <li key={id} className="mono wrap">
                  {id}
                </li>
              ))}
            </ul>
            <h3>Contradicts</h3>
            <ul>
              {item.contradicting.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <h3>Unresolved</h3>
            <ul>
              {item.missing_evidence.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>
        ))}
        <div className="versus" aria-hidden="true">
          vs
        </div>
      </div>
      <p>
        <Link to="/reasoning">Reasoning theatre</Link>
        {" · "}
        <Link to="/defence">Defence lab</Link>
      </p>
    </div>
  );
}
