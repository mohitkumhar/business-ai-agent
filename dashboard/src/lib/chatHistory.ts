export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  intent?: string | null;
  timestamp: number;
}

export interface ChatConversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "iba_chat_history";
const PENDING_DELETES_KEY = "iba_chat_history_pending_deletes";

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage quota failures and continue with in-memory state.
  }
}

function toTimestamp(value: unknown, fallback = Date.now()): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) return numeric;
    const parsed = Date.parse(value);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return fallback;
}

export function normalizeMessage(raw: unknown): ChatMessage | null {
  if (!raw || typeof raw !== "object") return null;
  const input = raw as Partial<ChatMessage> & { created_at?: string };
  const role = input.role === "assistant" ? "assistant" : input.role === "user" ? "user" : null;
  const content = typeof input.content === "string" ? input.content : "";
  if (!role || !content.trim()) return null;
  return {
    role,
    content,
    intent: typeof input.intent === "string" ? input.intent : null,
    timestamp: toTimestamp(input.timestamp ?? input.created_at),
  };
}

export function normalizeConversation(raw: unknown): ChatConversation | null {
  if (!raw || typeof raw !== "object") return null;
  const input = raw as Partial<ChatConversation> & {
    created_at?: string;
    updated_at?: string;
  };
  const id = String(input.id ?? "").trim();
  if (!id) return null;
  const messages = Array.isArray(input.messages)
    ? input.messages.map(normalizeMessage).filter((message): message is ChatMessage => message !== null)
    : [];
  const createdAt = toTimestamp(input.createdAt ?? input.created_at, messages[0]?.timestamp ?? Date.now());
  const updatedAt = toTimestamp(
    input.updatedAt ?? input.updated_at,
    messages[messages.length - 1]?.timestamp ?? createdAt
  );
  return {
    id,
    title: String(input.title ?? "New Chat").trim() || "New Chat",
    messages: messages.sort((left, right) => left.timestamp - right.timestamp),
    createdAt,
    updatedAt,
  };
}

function mergeMessages(primary: ChatMessage[], secondary: ChatMessage[]): ChatMessage[] {
  const merged = new Map<string, ChatMessage>();
  for (const message of [...primary, ...secondary]) {
    const key = `${message.role}:${message.timestamp}:${message.content}`;
    const existing = merged.get(key);
    merged.set(key, existing ? { ...existing, intent: existing.intent ?? message.intent ?? null } : message);
  }
  return [...merged.values()].sort((left, right) => left.timestamp - right.timestamp);
}

function pickConversationTitle(first: ChatConversation, second: ChatConversation, preferFirst: boolean) {
  const preferred = preferFirst ? first : second;
  const fallback = preferFirst ? second : first;
  if (preferred.title !== "New Chat") return preferred.title;
  if (fallback.title !== "New Chat") return fallback.title;
  return preferred.title || fallback.title || "New Chat";
}

export function mergeConversations(remote: ChatConversation[], local: ChatConversation[]): ChatConversation[] {
  const merged = new Map<string, ChatConversation>();

  for (const conversation of [...remote, ...local]) {
    const existing = merged.get(conversation.id);
    if (!existing) {
      merged.set(conversation.id, conversation);
      continue;
    }

    const preferExisting = existing.updatedAt >= conversation.updatedAt;
    const preferred = preferExisting ? existing : conversation;
    const other = preferExisting ? conversation : existing;
    const messages = mergeMessages(preferred.messages, other.messages);
    const latestMessageAt = messages[messages.length - 1]?.timestamp ?? 0;

    merged.set(conversation.id, {
      id: preferred.id,
      title: pickConversationTitle(preferred, other, true),
      createdAt: Math.min(preferred.createdAt, other.createdAt),
      updatedAt: Math.max(preferred.updatedAt, other.updatedAt, latestMessageAt),
      messages,
    });
  }

  return [...merged.values()].sort((left, right) => right.updatedAt - left.updatedAt);
}

export function loadConversations(): ChatConversation[] {
  return readJson<unknown[]>(STORAGE_KEY, [])
    .map(normalizeConversation)
    .filter((conversation): conversation is ChatConversation => conversation !== null)
    .sort((left, right) => right.updatedAt - left.updatedAt);
}

export function saveConversations(conversations: ChatConversation[]): { success: boolean; prunedCount: number } {
  if (typeof window === "undefined") return { success: true, prunedCount: 0 };
  
  const currentList = [...conversations];
  let prunedCount = 0;
  
  while (currentList.length > 0) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(currentList));
      return { success: true, prunedCount };
    } catch (err) {
      if (
        err instanceof DOMException &&
        (err.name === "QuotaExceededError" ||
          err.name === "NS_ERROR_DOM_QUOTA_REACHED" ||
          err.code === 22 ||
          err.code === 1014)
      ) {
        if (currentList.length > 1) {
          currentList.pop(); // Remove the oldest conversation
          prunedCount++;
          continue;
        }
      }
      console.error("Failed to save conversations to localStorage:", err);
      break;
    }
  }
  return { success: false, prunedCount };
}

export function loadPendingDeletes(): string[] {
  return readJson<unknown[]>(PENDING_DELETES_KEY, [])
    .map((value) => String(value))
    .filter(Boolean);
}

export function savePendingDeletes(conversationIds: string[]) {
  writeJson(PENDING_DELETES_KEY, [...new Set(conversationIds)]);
}

export function queuePendingDelete(conversationId: string) {
  savePendingDeletes([...loadPendingDeletes(), conversationId]);
}

export function clearPendingDelete(conversationId: string) {
  savePendingDeletes(loadPendingDeletes().filter((id) => id !== conversationId));
}

export function createConversation(): ChatConversation {
  return {
    id: crypto.randomUUID(),
    title: "New Chat",
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

export function deriveTitle(message: string): string {
  const trimmed = message.trim();
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}…` : trimmed;
}
