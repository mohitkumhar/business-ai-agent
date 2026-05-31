import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.AGENT_API_URL || "http://localhost:5000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/employees`, { cache: 'no-store' });
    if (!res.ok) {
      return NextResponse.json({ error: "Failed to fetch employees" }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Failed to fetch employees";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
