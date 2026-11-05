import { describe, expect, it } from "vitest";
import { formatTime, severityTone, shortId } from "./format";

describe("format helpers", () => {
  it("shortens identifiers", () => {
    expect(shortId("1234")).toBe("1234");
    expect(shortId("11111111-1111-4111-8111-111111111111")).toContain("…");
  });

  it("maps severity", () => {
    expect(severityTone("high")).toBe("crit");
    expect(severityTone("active")).toBe("ok");
  });

  it("formats timestamps", () => {
    expect(formatTime(undefined)).toBe("—");
    expect(formatTime("2026-11-04T14:00:00+00:00")).toContain("2026-11-04");
  });
});
