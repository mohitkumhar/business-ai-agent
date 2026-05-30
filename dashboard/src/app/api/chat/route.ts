import { NextRequest } from "next/server";

/**
 * POST /api/chat
 * Server-side SSE proxy to the Flask agent.
 *
 * Why a route handler instead of a Next.js rewrite?
 *  1. `rewrites()` bakes the destination at BUILD time — in Docker
 *     the env var doesn't exist yet, so it falls back to localhost.
 *  2. Next.js rewrites buffer the response — SSE events are not
 *     streamed to the browser in real-time.
 *
 * This route reads AGENT_API_URL at **runtime** and pipes the
 * Flask SSE stream byte-for-byte to the client with proper headers.
 */
export async function POST(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const inputQuery = searchParams.get("input-query") ?? "";
  const threadId = searchParams.get("thread-id") ?? "";

  if (!inputQuery || !threadId) {
    return new Response(
      JSON.stringify({ error: "input-query and thread-id are required" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  const agentUrl =
    process.env.AGENT_API_URL || "http://localhost:5000";

  const params = new URLSearchParams({
    "input-query": inputQuery,
    "thread-id": threadId,
  });
  const authorization = req.headers.get("authorization");
  const headers: Record<string, string> = { Accept: "text/event-stream" };
  if (authorization) headers.Authorization = authorization;

  try {
    const upstream = await fetch(
      `${agentUrl}/api/v1/query?${params.toString()}`,
      {
        method: "POST",
        headers,
        // @ts-expect-error -- Node 18+ undici supports duplex
        duplex: "half",
      }
    );

    if (!upstream.ok) {
      const text = await upstream.text();
      return new Response(text, {
        status: upstream.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    // Pipe the SSE stream straight through
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err) {
    console.error("[chat proxy] upstream error:", err);
    return new Response(
      JSON.stringify({ error: "Failed to reach backend agent" }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

// Ensure Next.js doesn't buffer the response body
export const dynamic = "force-dynamic";
