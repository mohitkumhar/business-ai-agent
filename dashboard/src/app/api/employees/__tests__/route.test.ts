/**
 * Unit tests for GET /api/employees
 *
 * Strategy:
 *  - Mock next/server so NextResponse.json() returns a plain inspectable object.
 *  - Spy on global.fetch so every test controls what the upstream "responds" with.
 *  - Manipulate process.env.AGENT_API_URL to verify URL-construction logic.
 */

import { GET } from "../route";

// ---------------------------------------------------------------------------
// Mock next/server
// NextResponse.json in production returns a Web API Response.
// In the test environment we return a plain object so we can inspect body & status.
// ---------------------------------------------------------------------------
jest.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown, init?: { status?: number }) => ({
      status: init?.status ?? 200,
      body,
      json: async () => body,
    }),
  },
}));

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type MockResponse = { status: number; body: unknown; json: () => Promise<unknown> };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeUpstreamOk(data: unknown, status = 200): Partial<Response> {
  return { ok: true, status, json: async () => data };
}

function makeUpstreamError(status: number): Partial<Response> {
  return { ok: false, status };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------
describe("GET /api/employees", () => {
  const ORIGINAL_ENV = process.env;
  let fetchSpy: jest.SpyInstance;

  beforeEach(() => {
    // Spy on global fetch — restored after each test
    fetchSpy = jest.spyOn(global, "fetch");

    // Reset env to a clean copy without AGENT_API_URL
    process.env = { ...ORIGINAL_ENV };
    delete process.env.AGENT_API_URL;
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    process.env = ORIGINAL_ENV;
  });

  // ─── Happy path ───────────────────────────────────────────────────────────

  describe("happy path", () => {
    it("returns 200 and forwards the JSON body from the upstream API", async () => {
      const employees = [
        { id: 1, name: "Alice" },
        { id: 2, name: "Bob" },
      ];
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk(employees));

      const res = (await GET()) as unknown as MockResponse;

      expect(res.status).toBe(200);
      expect(res.body).toEqual(employees);
    });
  });

  // ─── URL construction ─────────────────────────────────────────────────────

  describe("URL construction", () => {
    it("uses the default base URL when AGENT_API_URL is not set", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk([]));

      await GET();

      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:5000/api/v1/employees",
        expect.any(Object)
      );
    });

    it("uses AGENT_API_URL when the environment variable is set", async () => {
      process.env.AGENT_API_URL = "http://custom-agent:8080";
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk([]));

      await GET();

      expect(fetchSpy).toHaveBeenCalledWith(
        "http://custom-agent:8080/api/v1/employees",
        expect.any(Object)
      );
    });

    it("always targets the /api/v1/employees path on the upstream", async () => {
      process.env.AGENT_API_URL = "https://prod.example.com";
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk([]));

      await GET();

      const calledUrl = fetchSpy.mock.calls[0][0] as string;
      expect(calledUrl).toMatch(/\/api\/v1\/employees$/);
    });
  });

  // ─── Cache options ────────────────────────────────────────────────────────

  describe("cache configuration", () => {
    it("always passes cache: no-store so employees are never served stale", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk([]));

      await GET();

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ cache: "no-store" })
      );
    });
  });

  // ─── Upstream error responses ─────────────────────────────────────────────

  describe("upstream HTTP errors", () => {
    it.each([
      [503, "Service Unavailable"],
      [404, "Not Found"],
      [401, "Unauthorized"],
      [500, "Internal Server Error"],
    ])(
      "proxies HTTP %i from upstream and returns the error message",
      async (upstreamStatus) => {
        fetchSpy.mockResolvedValueOnce(makeUpstreamError(upstreamStatus));

        const res = (await GET()) as unknown as MockResponse;

        expect(res.status).toBe(upstreamStatus);
        expect(res.body).toEqual({ error: "Failed to fetch employees" });
      }
    );
  });

  // ─── Network / fetch-level errors ─────────────────────────────────────────

  describe("network errors (fetch throws)", () => {
    it("returns 500 and forwards err.message when fetch throws an Error", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("ECONNREFUSED"));

      const res = (await GET()) as unknown as MockResponse;

      expect(res.status).toBe(500);
      expect(res.body).toEqual({ error: "ECONNREFUSED" });
    });

    it("returns 500 with fallback message when fetch throws a non-Error string", async () => {
      fetchSpy.mockRejectedValueOnce("upstream exploded");

      const res = (await GET()) as unknown as MockResponse;

      expect(res.status).toBe(500);
      expect(res.body).toEqual({ error: "Failed to fetch employees" });
    });

    it("returns 500 with fallback message when fetch throws null", async () => {
      fetchSpy.mockRejectedValueOnce(null);

      const res = (await GET()) as unknown as MockResponse;

      expect(res.status).toBe(500);
      expect(res.body).toEqual({ error: "Failed to fetch employees" });
    });

    it("returns 500 with fallback message when fetch throws a plain object", async () => {
      fetchSpy.mockRejectedValueOnce({ code: "TIMEOUT" });

      const res = (await GET()) as unknown as MockResponse;

      expect(res.status).toBe(500);
      expect(res.body).toEqual({ error: "Failed to fetch employees" });
    });
  });
});
