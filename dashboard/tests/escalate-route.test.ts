import { describe, expect, it, beforeEach, afterEach } from "bun:test";
import { POST } from "../src/app/api/escalate/route";

describe("POST /api/escalate", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = originalFetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns ok when upstream succeeds", async () => {
    global.fetch = async () =>
      ({
        ok: true,
        json: async () => ({}),
        text: async () => "",
      }) as any;

    const req = new Request("http://localhost", {
      method: "POST",
      body: JSON.stringify({ test: "data" }),
    });

    const res = await POST(req as any);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data).toEqual({ status: "ok" });
  });

  it("returns upstream error when backend fails", async () => {
    global.fetch = async () =>
      ({
        ok: false,
        status: 400,
        text: async () => "bad request from upstream",
      }) as any;

    const req = new Request("http://localhost", {
      method: "POST",
      body: JSON.stringify({ test: "data" }),
    });

    const res = await POST(req as any);
    const data = await res.json();

    expect(res.status).toBe(400);
    expect(data).toEqual({ error: "bad request from upstream" });
  });

  it("returns 502 when fetch throws", async () => {
    global.fetch = async () => {
      throw new Error("network down");
    };

    const req = new Request("http://localhost", {
      method: "POST",
      body: JSON.stringify({ test: "data" }),
    });

    const res = await POST(req as any);
    const data = await res.json();

    expect(res.status).toBe(502);
    expect(data).toEqual({ error: "Failed to reach backend agent" });
  });
});