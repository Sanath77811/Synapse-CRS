import type { FindingView, SupportingEventView } from "../api/types";

/** Findings may share supporting events. List each event id once. */
export function uniqueSupportingEvents(
  findings: Pick<FindingView, "supporting_events">[],
): SupportingEventView[] {
  const seen = new Set<string>();
  const events: SupportingEventView[] = [];
  for (const finding of findings) {
    for (const event of finding.supporting_events) {
      if (seen.has(event.event_id)) {
        continue;
      }
      seen.add(event.event_id);
      events.push(event);
    }
  }
  return events;
}
