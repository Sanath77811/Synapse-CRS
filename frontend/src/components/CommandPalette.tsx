import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformContext } from "../context/PlatformContext";

const ROUTES = [
  { to: "/", label: "Command Centre" },
  { to: "/telemetry", label: "Telemetry Operations" },
  { to: "/evidence", label: "Evidence Lab" },
  { to: "/investigations", label: "Investigation Studio" },
  { to: "/graph", label: "Threat Graph" },
  { to: "/reasoning", label: "Reasoning Engine" },
  { to: "/hypotheses", label: "Hypothesis Arena" },
  { to: "/defence", label: "Defence Lab" },
  { to: "/research", label: "Research Observatory" },
  { to: "/control", label: "System Control" },
  { to: "/session", label: "Session" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const { data, enterDemo, refresh } = usePlatformContext();

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const items = useMemo(() => {
    const extra = [
      ...data.targets.map((item) => ({ to: "/telemetry", label: `Target ${item.name}` })),
      ...data.cases.map((item) => ({ to: `/investigations/${item.id}`, label: `Case ${item.state}` })),
      { to: "/", label: "Refresh snapshot", action: "refresh" as const },
      { to: "/", label: "Enter demonstration mode", action: "demo" as const },
    ];
    const all = [...ROUTES.map((item) => ({ ...item, action: "nav" as const })), ...extra];
    const q = query.trim().toLowerCase();
    return q ? all.filter((item) => item.label.toLowerCase().includes(q)) : all;
  }, [data.cases, data.targets, query]);

  if (!open) {
    return null;
  }
  return (
    <div className="palette-back" role="dialog" aria-label="Command palette">
      <div className="palette">
        <input
          autoFocus
          value={query}
          placeholder="Jump to workspace, target, or case"
          onChange={(event) => setQuery(event.target.value)}
        />
        <ul>
          {items.slice(0, 12).map((item) => (
            <li key={`${item.to}-${item.label}`}>
              <button
                type="button"
                onClick={() => {
                  if ("action" in item && item.action === "refresh") {
                    refresh();
                  } else if ("action" in item && item.action === "demo") {
                    enterDemo();
                  } else {
                    navigate(item.to);
                  }
                  setOpen(false);
                  setQuery("");
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
        <p className="dim">Ctrl/Cmd+K · Esc closes. Actions only navigate or refresh; nothing is executed on a host.</p>
      </div>
    </div>
  );
}
