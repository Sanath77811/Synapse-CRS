import { severityTone } from "../lib/format";

export function StatusChip({ label }: { label: string }) {
  return <span className={`chip chip-${severityTone(label.toLowerCase())}`}>{label}</span>;
}
