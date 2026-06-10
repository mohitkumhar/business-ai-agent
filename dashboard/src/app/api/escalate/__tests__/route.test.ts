import { POST } from "../route";

jest.mock("next/server", () => ({
  NextResponse: {
    json: (body: unknown, init?: { status?: number }) => ({
      status: init?.status ?? 200,
      body,
      json: async () => body,
    }),
  },
}));

type MockResponse = { status: number; body: unknown; json: () => Promise<unknown> };
type PostRequest = Parameters<typeof POST>[0];

function makeRequest(headers?: HeadersInit, body: unknown = { query: "help" }): PostRequest {
  return {
    headers: new Headers(headers),
    json: async () => body,
  } as PostRequest;
}

describe("POST /api/escalate", () => {
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

  it("returns 401 before contacting the backend when Authorization is missing", async () => {
    const res = (await POST(makeRequest({ "Content-Type": "application/json" }))) as MockResponse;

    expect(res.status).toBe(401);
    expect(res.body).toEqual({ error: "Authorization header is required" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the incoming Authorization header to the Flask escalation endpoint", async () => {
    fetchSpy.mockResolvedValueOnce({
      ok: true,
      status: 200,
    });

    const res = (await POST(
      makeRequest(
        {
          Authorization: "Bearer user-token",
          "Content-Type": "application/json",
        },
        { query: "Need help", summary: "Context", assignee_name: "Alice" }
      )
    )) as MockResponse;

    expect(res.status).toBe(200);
    expect(res.body).toEqual({ status: "ok" });
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:5000/api/v1/escalate",
      expect.objectContaining({
        method: "POST",
        headers: {
          Authorization: "Bearer user-token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: "Need help",
          summary: "Context",
          assignee_name: "Alice",
        }),
      })
    );
  });
});
