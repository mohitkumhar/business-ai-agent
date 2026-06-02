import { NextRequest } from "next/server";

import { proxyChatHistoryRequest } from "../../../proxy";

type RouteContext = {
  params: Promise<{
    conversationId: string;
  }>;
};

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest, context: RouteContext) {
  const { conversationId } = await context.params;
  return proxyChatHistoryRequest(
    req,
    `/api/chat/conversations/${encodeURIComponent(conversationId)}/messages`
  );
}
