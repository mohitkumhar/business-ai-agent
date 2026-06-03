import { NextRequest, NextResponse } from "next/server";

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
      const text = await upstream.text();
      return NextResponse.json({ error: text }, { status: upstream.status });
    }
    
    return NextResponse.json({ status: "ok" });
  } catch (err: unknown) {
    console.error("[escalate proxy] err:", err);
    return NextResponse.json({ error: "Failed to reach backend agent" }, { status: 502 });
  }
}
