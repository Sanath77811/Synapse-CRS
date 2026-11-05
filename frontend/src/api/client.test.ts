import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiRequest", () => {
  it("maps nested API error envelopes without echoing tokens", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({
            error: { code: "authentication_failed", message: "The bearer token was rejected." },
          }),
      })),
    );
    await expect(apiRequest("/api/v1/targets", { token: "secret-token-value" })).rejects.toMatchObject({
      status: 401,
      code: "authentication_failed",
      message: "The bearer token was rejected.",
    });
  });

  it("keeps authentication_required distinct from a rejected token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 401,
        text: async () =>
          JSON.stringify({
            error: { code: "authentication_required", message: "A bearer token is required." },
          }),
      })),
    );
    await expect(apiRequest("/api/v1/targets")).rejects.toMatchObject({
      status: 401,
      code: "authentication_required",
    });
  });

  it("maps 403 and 422", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 403,
        text: async () => JSON.stringify({ message: "admin only" }),
      })),
    );
    await expect(apiRequest("/x")).rejects.toBeInstanceOf(ApiError);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        text: async () => JSON.stringify({ message: "invalid" }),
      })),
    );
    await expect(apiRequest("/x")).rejects.toMatchObject({ code: "validation_failed" });
  });

  it("returns a network error when fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    await expect(apiRequest("/health")).rejects.toMatchObject({ code: "network", status: 0 });
  });

  it("parses JSON on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ status: "ok" }),
      })),
    );
    await expect(apiRequest<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
  });
});
