import { NextRequest, NextResponse } from "next/server";

async function readJsonSafe(res: Response) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

function logError(err: unknown) {
  console.error("[escalate proxy] err:", err);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const agentUrl = process.env.AGENT_API_URL || "http://localhost:5000";
    const upstream = await fetch(`${agentUrl}/api/v1/escalate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!upstream.ok) {
      const payload = await readJsonSafe(upstream);
      const message =
        typeof payload?.error === "string"
          ? payload.error
          : "Escalation failed in the backend agent";
      return NextResponse.json({ error: message }, { status: upstream.status });
    }

    const payload = await readJsonSafe(upstream);
    return NextResponse.json(payload ?? { status: "ok" });
  } catch (err: unknown) {
    logError(err);
    return NextResponse.json({ error: "Failed to reach backend agent" }, { status: 502 });
  }
}
