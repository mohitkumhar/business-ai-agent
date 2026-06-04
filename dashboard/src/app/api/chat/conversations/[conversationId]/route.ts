import { NextRequest } from "next/server";

import { proxyChatHistoryRequest } from "../../proxy";

type RouteContext = {
  params: Promise<{
    conversationId: string;
  }>;
};

export const dynamic = "force-dynamic";

function conversationPath(conversationId: string) {
  return `/api/chat/conversations/${encodeURIComponent(conversationId)}`;
}

export async function GET(req: NextRequest, context: RouteContext) {
  const { conversationId } = await context.params;
  return proxyChatHistoryRequest(req, conversationPath(conversationId));
}

export async function PUT(req: NextRequest, context: RouteContext) {
  const { conversationId } = await context.params;
  return proxyChatHistoryRequest(req, conversationPath(conversationId));
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  const { conversationId } = await context.params;
  return proxyChatHistoryRequest(req, conversationPath(conversationId));
}
