import { NavLink, Outlet } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";
import { maskToken } from "../auth/session";
import { StatusChip } from "../components/StatusChip";

const LINKS = [
  { to: "/", label: "Command", caption: "Centre" },
  { to: "/telemetry", label: "Telemetry", caption: "Operations" },
  { to: "/evidence", label: "Evidence", caption: "Lab" },
  { to: "/investigations", label: "Investigation", caption: "Studio" },
  { to: "/graph", label: "Threat", caption: "Graph" },
  { to: "/reasoning", label: "Reasoning", caption: "Engine" },
  { to: "/hypotheses", label: "Hypothesis", caption: "Arena" },
  { to: "/defence", label: "Defence", caption: "Lab" },
  { to: "/research", label: "Research", caption: "Observatory" },
  { to: "/control", label: "System", caption: "Control" },
];

export function Shell() {
  const { mode, token, health, ready, healthError, signOut, enterDemo } = usePlatformContext();
  return (
    <div className="shell">
      <a className="skip" href="#workspace">
        Skip to workspace
      </a>
      <aside className="rail" aria-label="Workspaces">
        <div className="brand">
          <span className="mark" aria-hidden="true" />
          <div>
            <strong>SYNAPSE</strong>
            <em>CRS</em>
          </div>
        </div>
        <nav>
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"} className="rail-link">
              <span>{link.label}</span>
              <small>{link.caption}</small>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="workspace-wrap">
        <header className="topbar">
          <p className="product">Neuro-symbolic investigation operating environment</p>
          <div className="top-status">
            {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
            <StatusChip label={health?.status === "ok" ? "api ok" : healthError ? "api down" : "api"} />
            <StatusChip label={ready?.status === "ready" ? "db ready" : "db unknown"} />
            {token ? <span className="mono muted">token {maskToken(token)}</span> : null}
            {mode === "live" ? (
              <button type="button" className="ghost" onClick={signOut}>
                Sign out
              </button>
            ) : (
              <button type="button" className="ghost" onClick={enterDemo}>
                Stay in demo
              </button>
            )}
          </div>
        </header>
        <main id="workspace" className="workspace">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
