import { useEffect, useState } from "react";

type Probe = {
  label: string;
  state: "loading" | "ok" | "down";
  detail: string;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function probe(path: string): Promise<Probe> {
  try {
    const response = await fetch(`${API_BASE}${path}`);
    const body: unknown = await response.json();
    if (!response.ok) {
      return { label: path, state: "down", detail: `HTTP ${response.status}` };
    }
    return { label: path, state: "ok", detail: JSON.stringify(body) };
  } catch {
    return { label: path, state: "down", detail: "API is not reachable" };
  }
}

export function App() {
  const [health, setHealth] = useState<Probe>({
    label: "/health",
    state: "loading",
    detail: "Checking",
  });
  const [ready, setReady] = useState<Probe>({
    label: "/ready",
    state: "loading",
    detail: "Checking",
  });

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [healthResult, readyResult] = await Promise.all([probe("/health"), probe("/ready")]);
      if (!cancelled) {
        setHealth(healthResult);
        setReady(readyResult);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main>
      <p className="eyebrow">Version 0.1 foundation</p>
      <h1>Synapse-CRS</h1>
      <p className="lede">
        Autonomous Runtime Cyber Defense and Formal Verification Platform. Project currently under
        active development.
      </p>
      <p>
        This screen reports whether the local control plane is up. It does not register targets,
        advance cases, or send commands.
      </p>

      <section aria-label="Service status">
        <h2>Local API</h2>
        <Status probe={health} />
        <Status probe={ready} />
        <p className="meta">API base: {API_BASE}</p>
      </section>

      <section>
        <h2>What v0.1 does</h2>
        <ul>
          <li>Registers owned targets with an owner, scope, expiry, and capability allowlist.</li>
          <li>Refuses expired, revoked, or out-of-scope targets.</li>
          <li>Stores the case pipeline and allows only the next valid state.</li>
          <li>Appends hash-chained audit events for registry changes.</li>
        </ul>
      </section>

      <section>
        <h2>What v0.1 does not do</h2>
        <ul>
          <li>It does not discover vulnerabilities or unknown flaws.</li>
          <li>It does not exploit systems or generate attacks.</li>
          <li>It does not patch binaries or apply runtime mitigations.</li>
          <li>It does not provide zero-downtime remediation.</li>
          <li>It does not mathematically prove that a system is secure.</li>
        </ul>
      </section>
    </main>
  );
}

function Status({ probe }: { probe: Probe }) {
  return (
    <p className={`status status-${probe.state}`}>
      <span>{probe.label}</span>
      <strong>{probe.state}</strong>
      <code>{probe.detail}</code>
    </p>
  );
}
