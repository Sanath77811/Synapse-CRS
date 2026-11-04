import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";

export function HypothesisArena() {
  const { data } = usePlatformContext();
  const assessment = data.assessments[0];
  const [left, setLeft] = useState(0);
  const [right, setRight] = useState(1);
  if (!assessment) {
    return (
      <div className="page">
        <PageHeader
          kicker="Hypothesis Arena"
          title="Competing explanations"
          summary="No hypotheses until an assessment exists."
        />
      </div>
    );
  }
  const a = assessment.hypotheses[left];
  const b = assessment.hypotheses[right];
  return (
    <div className="page">
      <PageHeader
        kicker="Hypothesis Arena"
        title="Compare explanations"
        summary="Support values are engine scores. They are not independent confirmation of malice."
      />
      <div className="compare">
        {[a, b].map((item, index) => (
          <section className="panel" key={item.hypothesis_id}>
            <label>
              Slot {index === 0 ? "A" : "B"}
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
            <StatusChip label={item.status} />
            <p>Support {item.support}</p>
            <p>{item.rationale}</p>
            <h3>Supporting events</h3>
            <ul>
              {item.supporting_event_ids.map((id) => (
                <li key={id} className="mono wrap">
                  {id}
                </li>
              ))}
            </ul>
            <h3>Contradicting</h3>
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
      </div>
    </div>
  );
}
