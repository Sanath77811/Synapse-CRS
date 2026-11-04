import { usePlatformContext } from "../context/PlatformContext";

export function DefenceLab() {
  const { data, mode } = usePlatformContext();
  const verification = data.assessments[0]?.verification;
  return (
    <div className="bench">
      <header>
        <p className="kicker">Defence lab</p>
        <h1>Policy verification bench</h1>
        <p className="dim">SAT is an encoded-policy result. It is not proof a real-world action is safe. No mitigation is executed here.</p>
        {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
      </header>
      {!verification ? (
        <p className="dim">No verification payload.</p>
      ) : (
        <div className="bench-grid">
          <section>
            <h2>{verification.kind}</h2>
            <p className="solver">{verification.solver_result}</p>
            <p>{verification.explanation}</p>
            <p className="dim">{verification.assumptions}</p>
          </section>
          <section>
            <h2>Constraints</h2>
            <ul className="circuit">
              {verification.constraints.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <h2>Violated</h2>
            {verification.violated.length === 0 ? <p className="dim">None reported.</p> : (
              <ul>
                {verification.violated.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
