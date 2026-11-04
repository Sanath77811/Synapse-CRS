import { NavLink, Outlet } from "react-router-dom";
import { maskToken } from "../auth/session";
import { usePlatformContext } from "../context/PlatformContext";

const LINKS = [
  { to: "/", mark: "⌘", label: "Command" },
  { to: "/telemetry", mark: "◎", label: "Telemetry" },
  { to: "/evidence", mark: "▣", label: "Evidence" },
  { to: "/investigations", mark: "▤", label: "Cases" },
  { to: "/graph", mark: "◈", label: "Graph" },
  { to: "/reasoning", mark: "λ", label: "Reasoning" },
  { to: "/hypotheses", mark: "⇔", label: "Hypotheses" },
  { to: "/defence", mark: "⬡", label: "Defence" },
  { to: "/research", mark: "π", label: "Research" },
  { to: "/control", mark: "⚙", label: "Control" },
];

export function Shell() {
  const { mode, token, health, ready, healthError, signOut, enterDemo } = usePlatformContext();
  const apiOk = health?.status === "ok";
  const dbOk = ready?.status === "ready";
  return (
    <div className="shell">
      <a className="skip" href="#workspace">
        Skip to workspace
      </a>
      <aside className="rail" aria-label="Workspaces">
        <NavLink to="/" end className="brand-lock">
          <span className="mark" />
          <span className="brand-copy">
            <b>SYNAPSE</b>
            <i>CRS</i>
          </span>
        </NavLink>
        <nav>
          {LINKS.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"} className="rail-link">
              <em>{link.mark}</em>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="stage">
        <header className="hud">
          <p className="hud-title">
            Investigation environment
            <span className="hud-sep">/</span>
            observer only
          </p>
          <div className="hud-cluster">
            {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
            <span className={apiOk ? "lamp lamp-ok" : "lamp lamp-off"}>
              API {apiOk ? "live" : healthError ? "refused" : "idle"}
            </span>
            <span className={dbOk ? "lamp lamp-ok" : "lamp lamp-off"}>DB {dbOk ? "ready" : "unknown"}</span>
            {token ? <span className="mono dim">tok {maskToken(token)}</span> : null}
            {mode === "live" ? (
              <button type="button" className="ghost" onClick={signOut}>
                Sign out
              </button>
            ) : (
              <button type="button" className="ghost" onClick={enterDemo}>
                Demo
              </button>
            )}
          </div>
        </header>
        <main id="workspace" className="viewport">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
