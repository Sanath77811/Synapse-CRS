import type { ReactNode } from "react";

export function DetailPanel({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  return (
    <aside className="detail-panel" aria-label={title}>
      <div className="detail-head">
        <h2>{title}</h2>
        <button type="button" className="ghost" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="detail-body">{children}</div>
    </aside>
  );
}

export function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="field">
      <span>{label}</span>
      <strong className={mono ? "mono wrap" : "wrap"}>{value}</strong>
    </div>
  );
}
