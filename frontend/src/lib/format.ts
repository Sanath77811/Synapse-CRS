export function shortId(value: string): string {
  return value.length > 12 ? `${value.slice(0, 8)}…${value.slice(-4)}` : value;
}

export function formatTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

export function severityTone(value: string): "ok" | "info" | "warn" | "crit" | "muted" {
  if (value === "high" || value === "down" || value === "revoked") {
    return "crit";
  }
  if (value === "medium" || value === "unusual") {
    return "warn";
  }
  if (value === "low" || value === "active" || value === "ok" || value === "ready") {
    return "ok";
  }
  if (value === "info" || value === "correlation") {
    return "info";
  }
  return "muted";
}
