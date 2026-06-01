import { NextRequest } from "next/server";

import { proxyChatHistoryRequest } from "../proxy";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  return proxyChatHistoryRequest(req, "/api/chat/conversations");
}
