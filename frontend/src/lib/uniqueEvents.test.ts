import { describe, expect, it } from "vitest";
import { uniqueSupportingEvents } from "./uniqueEvents";

const event = (id: string) => ({
  event_id: id,
  event_type: "network_connection_observed",
  observed_at: "2026-11-05T01:30:00Z",
  sequence: 1,
  agent_id: "a",
  boot_id: "b",
});

describe("uniqueSupportingEvents", () => {
  it("keeps one row per event id when findings share evidence", () => {
    const shared = event("e1");
    const findings = [
      { supporting_events: [shared, event("e2")] },
      { supporting_events: [shared, event("e3")] },
    ];
    expect(uniqueSupportingEvents(findings).map((item) => item.event_id)).toEqual(["e1", "e2", "e3"]);
  });
});
