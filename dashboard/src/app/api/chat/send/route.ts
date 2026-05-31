import { NextRequest } from "next/server";

/**
 * POST /api/chat/send
 * Runtime SSE proxy to the agent's chat endpoint.
 *
 * Next.js rewrites buffer streaming responses; this route pipes
 * `text/event-stream` from the Flask agent without buffering.
 */
export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const agentUrl = process.env.AGENT_API_URL || "http://localhost:5000";
  const authorization = req.headers.get("authorization");

  try {
    const upstream = await fetch(`${agentUrl}/api/chat/send`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...(authorization ? { Authorization: authorization } : {}),
      },
      body: JSON.stringify(body),
      // @ts-expect-error -- Node 18+ undici supports duplex for streaming bodies
      duplex: "half",
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      return new Response(text, {
        status: upstream.status,
        headers: {
          "Content-Type":
            upstream.headers.get("Content-Type") ?? "application/json",
        },
      });
    }

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
    console.error("[chat/send proxy] upstream error:", err);
    return new Response(
      JSON.stringify({ error: "Failed to reach backend agent" }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}

export const dynamic = "force-dynamic";
