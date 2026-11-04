import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { maskToken } from "../auth/session";
import { CommandPalette } from "../components/CommandPalette";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { usePlatformContext } from "../context/PlatformContext";

export const LINKS = [
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
  const location = useLocation();
  const {
    mode,
    token,
    health,
    ready,
    healthError,
    signOut,
    enterDemo,
    refresh,
    selectedTarget,
    source,
    error,
    authStatus,
  } = usePlatformContext();
  const apiOk = health?.status === "ok";
  const dbOk = ready?.status === "ready";
  const workspace = LINKS.find((item) =>
    item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to),
  );
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
            {workspace?.label ?? "Workspace"}
            <span className="hud-sep">/</span>
            {selectedTarget?.name ?? "no target lock"}
            <span className="hud-sep">/</span>
            {source}
          </p>
          <div className="hud-cluster">
            {mode === "demo" ? <span className="demo-flag">DEMO MODE</span> : null}
            <span className={apiOk ? "lamp lamp-ok" : "lamp lamp-off"}>
              API {apiOk ? "live" : healthError ? "refused" : "idle"}
            </span>
            <span className={dbOk ? "lamp lamp-ok" : "lamp lamp-off"}>
              DB {dbOk ? "ready" : "unknown"}
            </span>
            {authStatus === "rejected" ? <span className="lamp lamp-off">auth rejected</span> : null}
            {token ? <span className="mono dim">tok {maskToken(token)}</span> : null}
            <Link className="ghost" to="/session">
              Session
            </Link>
            <button type="button" className="ghost" onClick={refresh}>
              Refresh
            </button>
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
        {error && mode === "live" ? <p className="error-banner hud-error">{error}</p> : null}
        <main id="workspace" className="viewport">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
