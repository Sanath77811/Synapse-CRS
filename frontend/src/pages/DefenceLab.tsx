import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { usePlatformContext } from "../context/PlatformContext";

export function DefenceLab() {
  const { data, mode } = usePlatformContext();
  const verification = data.assessments[0]?.verification;
  return (
    <div className="page">
      <PageHeader
        kicker="Defence Lab"
        title="Policy verification"
        summary="Z3 checks an encoded recommendation policy. SAT does not prove that a real-world action is safe. This console cannot execute isolation, firewall changes, or in-memory patches."
      />
      {mode === "demo" ? <p className="demo-flag">Synthetic verification record</p> : null}
      {!verification ? (
        <p className="muted">No verification payload. Admin POST verify is required in live mode.</p>
      ) : (
        <section className="panel">
          <h2>{verification.kind}</h2>
          <p>
            <StatusChip label={verification.solver_result} /> {verification.status} · policy{" "}
            {verification.policy_version}
          </p>
          <p>{verification.explanation}</p>
          <p className="muted">{verification.assumptions}</p>
          <h3>Constraints</h3>
          <ul>
            {verification.constraints.map((item) => (
              <li key={item} className="mono">
                {item}
              </li>
            ))}
          </ul>
          <h3>Violated</h3>
          {verification.violated.length === 0 ? <p className="muted">None reported.</p> : (
            <ul>
              {verification.violated.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
