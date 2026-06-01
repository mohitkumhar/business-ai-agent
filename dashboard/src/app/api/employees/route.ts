import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Failed to fetch employees";
}

export async function GET() {
  const apiUrl = process.env.AGENT_API_URL || "http://localhost:5000";
  try {
    const res = await fetch(`${apiUrl}/api/v1/employees`, { cache: "no-store" });
    if (!res.ok) {
      return NextResponse.json({ error: "Failed to fetch employees" }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (err: unknown) {
    return NextResponse.json({ error: getErrorMessage(err) }, { status: 500 });
  }
}
