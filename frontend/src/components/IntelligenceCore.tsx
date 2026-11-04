import { useMemo } from "react";
import { usePlatformContext } from "../context/PlatformContext";

type Mark = { id: string; label: string; kind: string; angle: number; r: number };

export function IntelligenceCore() {
  const { data, selectedTarget, health } = usePlatformContext();
  const marks = useMemo(() => {
    const items: Mark[] = [];
    data.targets.forEach((item, index) => {
      items.push({
        id: item.id,
        label: item.name,
        kind: "target",
        angle: (index / Math.max(data.targets.length, 1)) * Math.PI * 2 - Math.PI / 2,
        r: 92,
      });
    });
    data.findings.forEach((item, index) => {
      items.push({
        id: item.id,
        label: item.finding_type.replaceAll("_", " "),
        kind: "finding",
        angle: (index / Math.max(data.findings.length, 1)) * Math.PI * 2 - Math.PI / 3,
        r: 148,
      });
    });
    data.assessments.forEach((item, index) => {
      items.push({
        id: item.id,
        label: item.selected_hypothesis,
        kind: "reason",
        angle: (index / Math.max(data.assessments.length, 1)) * Math.PI * 2 + Math.PI / 5,
        r: 198,
      });
    });
    return items;
  }, [data]);
  const cx = 260;
  const cy = 240;
  return (
    <svg className="intel-core" viewBox="0 0 520 480" role="img" aria-label="Intelligence core">
      <defs>
        <radialGradient id="coreGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="rgba(94,234,212,0.22)" />
          <stop offset="100%" stopColor="rgba(94,234,212,0)" />
        </radialGradient>
      </defs>
      <circle cx={cx} cy={cy} r="220" fill="url(#coreGlow)" />
      {[70, 118, 168, 218].map((r) => (
        <circle key={r} cx={cx} cy={cy} r={r} className="orbit" />
      ))}
      {marks.map((mark) => {
        const x = cx + Math.cos(mark.angle) * mark.r;
        const y = cy + Math.sin(mark.angle) * mark.r;
        return (
          <g key={mark.id}>
            <line x1={cx} y1={cy} x2={x} y2={y} className={`spoke spoke-${mark.kind}`} />
            <circle cx={x} cy={y} r="5.5" className={`dot dot-${mark.kind}`} />
            <text x={x + 10} y={y + 4} className="orbit-label">
              {mark.label.slice(0, 28)}
            </text>
          </g>
        );
      })}
      <circle cx={cx} cy={cy} r="36" className="nucleus" />
      <text x={cx} y={cy - 4} textAnchor="middle" className="nucleus-title">
        SYNAPSE
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="nucleus-sub">
        {selectedTarget?.name ?? "no target"}
      </text>
      <text x={cx} y={cy + 28} textAnchor="middle" className="nucleus-sub">
        api {health?.status ?? "offline"}
      </text>
    </svg>
  );
}
