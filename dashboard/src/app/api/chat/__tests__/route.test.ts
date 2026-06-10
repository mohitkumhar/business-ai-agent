/**
 * Unit tests for POST /api/chat
 *
 * Strategy:
 *  - Build a minimal NextRequest-shaped object (the handler only touches
 *    req.url and req.headers.get(), so a plain cast is sufficient).
 *  - Spy on global.fetch to control upstream behaviour without real I/O.
 *  - Manipulate process.env.AGENT_API_URL to exercise URL-construction logic.
 *  - Inspect returned Web-API Response objects directly — Node 18+ exposes
 *    Response / Headers as globals so .status, .headers.get(), .json(),
 *    and .text() all work in the node test environment.
 *
 * No next/server mock is needed: the handler uses bare `new Response()`
 * (not NextResponse.json), so nothing from Next.js runs at test time.
 */

import type { NextRequest } from "next/server";
import { POST } from "../route";

// ---------------------------------------------------------------------------
// Request factory
// ---------------------------------------------------------------------------

function makeReq(
  searchParams: Record<string, string>,
  headers: Record<string, string> = {}
): NextRequest {
  const url = new URL("http://localhost:3000/api/chat");
  for (const [k, v] of Object.entries(searchParams)) {
    url.searchParams.set(k, v);
  }

  // Normalise to lowercase so get("authorization") matches { Authorization: "..." }
  const norm: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    norm[k.toLowerCase()] = v;
  }

  return {
    url: url.toString(),
    headers: { get: (name: string) => norm[name.toLowerCase()] ?? null },
  } as unknown as NextRequest;
}

// ---------------------------------------------------------------------------
// Upstream response factories
// ---------------------------------------------------------------------------

function makeUpstreamOk(): Partial<Response> {
  // body:null is enough — the handler pipes it straight through;
  // our tests only inspect status and headers, not body content.
  return { ok: true, status: 200, body: null };
}

function makeUpstreamError(
  status: number,
  text = "upstream error"
): Partial<Response> {
  return { ok: false, status, text: async () => text };
}

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const VALID_PARAMS = {
  "input-query": "What is my revenue?",
  "thread-id": "t-123",
};
const VALID_HEADERS = { authorization: "Bearer test-token" };

// ---------------------------------------------------------------------------
// Suite
// ---------------------------------------------------------------------------

describe("POST /api/chat", () => {
  const ORIGINAL_ENV = process.env;
  let fetchSpy: jest.SpyInstance;

  beforeEach(() => {
    fetchSpy = jest.spyOn(global, "fetch");
    process.env = { ...ORIGINAL_ENV };
    delete process.env.AGENT_API_URL;
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    process.env = ORIGINAL_ENV;
  });

  // ─── Parameter validation (400) ───────────────────────────────────────────

  describe("parameter validation (400)", () => {
    it("returns 400 when input-query is missing", async () => {
      const res = await POST(makeReq({ "thread-id": "t-1" }, VALID_HEADERS));
      expect(res.status).toBe(400);
      expect(await res.json()).toEqual({
        error: "input-query and thread-id are required",
      });
    });

    it("returns 400 when thread-id is missing", async () => {
      const res = await POST(makeReq({ "input-query": "hello" }, VALID_HEADERS));
      expect(res.status).toBe(400);
      expect(await res.json()).toEqual({
        error: "input-query and thread-id are required",
      });
    });

    it("returns 400 when both params are missing", async () => {
      const res = await POST(makeReq({}, VALID_HEADERS));
      expect(res.status).toBe(400);
    });

    it("returns 400 when input-query is an empty string", async () => {
      // searchParams.get() returns "" for ?input-query=; ?? doesn't trap it,
      // but !inputQuery does — empty string is treated as absent.
      const res = await POST(
        makeReq({ "input-query": "", "thread-id": "t-1" }, VALID_HEADERS)
      );
      expect(res.status).toBe(400);
    });

    it("returns 400 when thread-id is an empty string", async () => {
      const res = await POST(
        makeReq({ "input-query": "hello", "thread-id": "" }, VALID_HEADERS)
      );
      expect(res.status).toBe(400);
    });

    it("sets Content-Type: application/json on the 400 response", async () => {
      const res = await POST(makeReq({}, VALID_HEADERS));
      expect(res.headers.get("Content-Type")).toBe("application/json");
    });

    it("does not call the upstream when params are invalid", async () => {
      await POST(makeReq({}, VALID_HEADERS));
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // ─── Authorization validation (401) ───────────────────────────────────────

  describe("authorization validation (401)", () => {
    it("returns 401 when the Authorization header is absent", async () => {
      const res = await POST(makeReq(VALID_PARAMS, {}));
      expect(res.status).toBe(401);
      expect(await res.json()).toEqual({
        error: "Authorization header is required",
      });
    });

    it("sets Content-Type: application/json on the 401 response", async () => {
      const res = await POST(makeReq(VALID_PARAMS, {}));
      expect(res.headers.get("Content-Type")).toBe("application/json");
    });

    it("does not call the upstream when authorization is missing", async () => {
      await POST(makeReq(VALID_PARAMS, {}));
      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // ─── URL construction ──────────────────────────────────────────────────────

  describe("URL construction", () => {
    it("uses http://localhost:5000 when AGENT_API_URL is not set", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:5000/api/chat/send",
        expect.any(Object)
      );
    });

    it("uses AGENT_API_URL when the environment variable is set", async () => {
      process.env.AGENT_API_URL = "http://agent-svc:9000";
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://agent-svc:9000/api/chat/send",
        expect.any(Object)
      );
    });

    it("always targets /api/chat/send on the upstream", async () => {
      process.env.AGENT_API_URL = "https://prod.example.com";
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      const calledUrl = fetchSpy.mock.calls[0][0] as string;
      expect(calledUrl).toMatch(/\/api\/chat\/send$/);
    });
  });

  // ─── Request forwarding ────────────────────────────────────────────────────

  describe("request forwarding to upstream", () => {
    it("forwards the Authorization header to the upstream", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, { authorization: "Bearer my-token" }));
      const init = fetchSpy.mock.calls[0][1] as Record<string, unknown>;
      expect((init.headers as Record<string, string>).Authorization).toBe(
        "Bearer my-token"
      );
    });

    it("sends conversation_id and message in the upstream request body", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(
        makeReq(
          { "input-query": "What is profit?", "thread-id": "t-42" },
          VALID_HEADERS
        )
      );
      const init = fetchSpy.mock.calls[0][1] as RequestInit;
      const body = JSON.parse(init.body as string);
      expect(body).toEqual({
        conversation_id: "t-42",
        message: "What is profit?",
      });
    });

    it("sets Accept: text/event-stream to request an SSE response", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      const init = fetchSpy.mock.calls[0][1] as Record<string, unknown>;
      expect((init.headers as Record<string, string>).Accept).toBe(
        "text/event-stream"
      );
    });

    it("uses POST as the upstream HTTP method", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: "POST" })
      );
    });

    it("passes duplex: half to support request streaming on Node 18+", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      const init = fetchSpy.mock.calls[0][1] as Record<string, unknown>;
      expect(init.duplex).toBe("half");
    });
  });

  // ─── Happy path — SSE proxy ────────────────────────────────────────────────

  describe("happy path — SSE proxy", () => {
    it("returns 200 when the upstream responds ok", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.status).toBe(200);
    });

    it("sets Content-Type: text/event-stream", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("Content-Type")).toBe("text/event-stream");
    });

    it("sets Cache-Control: no-cache, no-transform to prevent proxy buffering", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("Cache-Control")).toBe("no-cache, no-transform");
    });

    it("sets Connection: keep-alive", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("Connection")).toBe("keep-alive");
    });

    it("sets X-Accel-Buffering: no to disable nginx buffering", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamOk());
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("X-Accel-Buffering")).toBe("no");
    });
  });

  // ─── Upstream HTTP errors ──────────────────────────────────────────────────

  describe("upstream HTTP errors", () => {
    it.each([
      [400, "bad request from agent"],
      [401, "unauthorized"],
      [404, "agent route not found"],
      [500, "internal agent error"],
      [503, "agent unavailable"],
    ])(
      "forwards HTTP %i from upstream with its text body",
      async (status, body) => {
        fetchSpy.mockResolvedValueOnce(makeUpstreamError(status, body));
        const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
        expect(res.status).toBe(status);
        expect(await res.text()).toBe(body);
      }
    );

    it("sets Content-Type: application/json on upstream error responses", async () => {
      fetchSpy.mockResolvedValueOnce(makeUpstreamError(503));
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("Content-Type")).toBe("application/json");
    });
  });

  // ─── Network errors (fetch throws) ────────────────────────────────────────

  describe("network errors (fetch throws)", () => {
    it("returns 502 with the standard error body when fetch throws an Error", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("ECONNREFUSED"));
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.status).toBe(502);
      expect(await res.json()).toEqual({
        error: "Failed to reach backend agent",
      });
    });

    it("returns 502 when fetch throws a non-Error string", async () => {
      fetchSpy.mockRejectedValueOnce("socket hang up");
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.status).toBe(502);
      expect(await res.json()).toEqual({
        error: "Failed to reach backend agent",
      });
    });

    it("returns 502 when fetch throws null", async () => {
      fetchSpy.mockRejectedValueOnce(null);
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.status).toBe(502);
    });

    it("returns 502 when fetch throws a plain object", async () => {
      fetchSpy.mockRejectedValueOnce({ code: "ETIMEDOUT" });
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.status).toBe(502);
    });

    it("sets Content-Type: application/json on 502 responses", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("timeout"));
      const res = await POST(makeReq(VALID_PARAMS, VALID_HEADERS));
      expect(res.headers.get("Content-Type")).toBe("application/json");
    });
  });
});