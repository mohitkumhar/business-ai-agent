import { describe, expect, it } from "bun:test";
import { parseUnknownClientError } from "./parseUnknownClientError";

describe("parseUnknownClientError", () => {
  it("returns string errors as the description", async () => {
    await expect(
      parseUnknownClientError({ err: "Request timed out", context: "billing" }),
    ).resolves.toEqual({
      context: "billing",
      description: "Request timed out",
      details: undefined,
    });
  });

  it("returns error messages with string causes as details", async () => {
    const error = new Error("Failed to save", { cause: "database offline" });

    await expect(parseUnknownClientError({ err: error })).resolves.toEqual({
      context: undefined,
      description: "Failed to save",
      details: "database offline",
    });
  });

  it("serializes non-string error causes", async () => {
    const error = new Error("Validation failed", {
      cause: { field: "email", reason: "invalid" },
    });

    await expect(parseUnknownClientError({ err: error })).resolves.toEqual({
      context: undefined,
      description: "Validation failed",
      details: '{"field":"email","reason":"invalid"}',
    });
  });

  it("reads response text from response-like errors", async () => {
    const error = Object.assign(new Error("API rejected request"), {
      response: {
        text: async () => "missing token",
      },
    });

    await expect(parseUnknownClientError({ err: error })).resolves.toEqual({
      context: undefined,
      description: "API rejected request",
      details: '"missing token"',
    });
  });

  it("serializes unknown object shapes", async () => {
    await expect(
      parseUnknownClientError({ err: { code: "UNKNOWN", retryable: false } }),
    ).resolves.toEqual({
      context: undefined,
      description: '{"code":"UNKNOWN","retryable":false}',
    });
  });

  it("falls back when parsing throws", async () => {
    const circular: { self?: unknown } = {};
    circular.self = circular;

    await expect(
      parseUnknownClientError({ err: circular, context: "checkout" }),
    ).resolves.toEqual({
      context: "checkout",
      description: "Unknown error (failed to parse)",
    });
  });
});
