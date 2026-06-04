import { NextRequest } from "next/server";

function jsonError(message: string, status: number) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function getAgentUrl(path: string, req: NextRequest) {
  const agentUrl = process.env.AGENT_API_URL || "http://localhost:5000";
  const search = new URL(req.url).search;
  return `${agentUrl}${path}${search}`;
}

async function buildUpstreamResponse(upstream: Response) {
  if (upstream.status === 204) {
    return new Response(null, { status: 204 });
  }

  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      "Cache-Control": "no-store",
    },
  });
}

export async function proxyChatHistoryRequest(req: NextRequest, path: string) {
  const authorization = req.headers.get("authorization");
  if (!authorization) {
    return jsonError("Authorization header is required", 401);
  }

  const hasBody = req.method !== "GET" && req.method !== "DELETE" && req.method !== "HEAD";
  const body = hasBody ? await req.text() : undefined;

  try {
    const upstream = await fetch(getAgentUrl(path, req), {
      method: req.method,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        Authorization: authorization,
        ...(body !== undefined
          ? { "Content-Type": req.headers.get("content-type") ?? "application/json" }
          : {}),
      },
      body,
    });

    return buildUpstreamResponse(upstream);
  } catch (error) {
    console.error("[chat history proxy] upstream error:", error);
    return jsonError("Failed to reach backend agent", 502);
  }
}
