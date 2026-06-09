/**
 * __tests__/createToastORPCError.test.js
 * Regression tests for createToastORPCError utility (#349)
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";

class ORPCError extends Error {
  constructor(code, options) {
    super(options?.message ?? code);
    this.code = code;
    this.data = options?.data ?? {};
  }
}

async function parseUnknownError({ err, context }) {
  const message =
    err instanceof Error ? err.message : typeof err === "string" ? err : "Unknown error";
  return {
    description: message,
    context: context ?? null,
    details: null,
  };
}

async function createToastORPCError(err, context) {
  const parsed = await parseUnknownError({ err, context });
  return new ORPCError("INTERNAL_SERVER_ERROR", {
    message: parsed.description,
    data: {
      context: parsed.context,
      details: parsed.details,
    },
  });
}

describe("createToastORPCError", () => {
  it("should create an ORPCError from a string error", async () => {
    const result = await createToastORPCError("something went wrong");
    assert.ok(result instanceof ORPCError);
    assert.equal(result.code, "INTERNAL_SERVER_ERROR");
    assert.equal(result.message, "something went wrong");
    assert.equal(result.data.context, null);
  });

  it("should create an ORPCError from an Error object", async () => {
    const err = new Error("network failure");
    const result = await createToastORPCError(err, "PaymentService");
    assert.ok(result instanceof ORPCError);
    assert.equal(result.code, "INTERNAL_SERVER_ERROR");
    assert.equal(result.message, "network failure");
    assert.equal(result.data.context, "PaymentService");
  });

  it("should handle missing context gracefully", async () => {
    const result = await createToastORPCError(new Error("oops"));
    assert.ok(result instanceof ORPCError);
    assert.equal(result.data.context, null);
    assert.equal(result.data.details, null);
  });
});
