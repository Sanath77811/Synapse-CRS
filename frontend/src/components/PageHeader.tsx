import type { ReactNode } from "react";

export function PageHeader({
  kicker,
  title,
  summary,
  actions,
}: {
  kicker: string;
  title: string;
  summary: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <p className="kicker">{kicker}</p>
        <h1>{title}</h1>
        <p className="summary">{summary}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}
