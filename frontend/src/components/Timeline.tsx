import type { TimelineItemView } from "../api/types";
import { formatTime, shortId } from "../lib/format";

export function Timeline({ items }: { items: TimelineItemView[] }) {
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={item.item_id} className={`tl tl-${item.classification}`}>
          <div className="tl-meta">
            <span className="mono">{formatTime(item.timestamp)}</span>
            <span className={`chip chip-${item.classification}`}>{item.classification}</span>
          </div>
          <p>{item.description}</p>
          <p className="muted mono">
            {item.event_type}
            {item.event_id ? ` · ${shortId(item.event_id)}` : ""}
          </p>
          <p className="muted">{item.uncertainty}</p>
        </li>
      ))}
    </ol>
  );
}
