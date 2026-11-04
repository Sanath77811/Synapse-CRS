import { describe, expect, it } from "vitest";
import { maskToken } from "./session";

describe("maskToken", () => {
  it("never returns the full token", () => {
    const token = "abcdefghijklmnopqrstuvwxyz";
    expect(maskToken(token)).not.toContain("abcdefghijkl");
    expect(maskToken(token).endsWith("wxyz")).toBe(true);
  });
});
