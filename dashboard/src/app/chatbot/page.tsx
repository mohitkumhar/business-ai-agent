"use client";
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { ChatbotIcon } from "@/components/Icons";
import {
  appendChatMessage,
  listChatConversations,
  removeChatConversation,
  upsertChatConversation,
} from "@/lib/api";
import {
  clearPendingDelete,
  createConversation,
  deriveTitle,
  loadConversations,
  loadPendingDeletes,
  mergeConversations,
  queuePendingDelete,
  saveConversations,
  savePendingDeletes,
  type ChatConversation,
  type ChatMessage,
} from "@/lib/chatHistory";
import MessageRenderer from "@/components/MessageRenderer";

interface CompletedNode {
  name: string;
  friendlyName: string;
}

type AgentStatus =
  | { kind: "idle" }
  | { kind: "connecting" }
  | { kind: "streaming"; label: string; node?: string }
  | { kind: "clarification"; text: string };

function friendlyNodeName(node: string): string {
  return node.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

type SyncStatus =
  | { kind: "loading"; label: string }
  | { kind: "syncing"; label: string }
  | { kind: "synced"; label: string }
  | { kind: "local"; label: string };

/* ─── Component ─── */
export default function ChatbotPage() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [status, setStatus] = useState<AgentStatus>({ kind: "idle" });
  const [syncStatus, setSyncStatus] = useState<SyncStatus>({ kind: "loading", label: "Loading history…" });
  const [historyOpen, setHistoryOpen] = useState(false);
  const [completedNodes, setCompletedNodes] = useState<CompletedNode[]>([]);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);

  const [employees, setEmployees] = useState<{login: string, avatar_url?: string, assigned_issues: number}[]>([]);
  const [escalatingMsgId, setEscalatingMsgId] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/employees", { cache: "no-store", headers: { "Cache-Control": "no-cache" } })
      .then(r => r.json())
      .then(d => {
         if (d.employees) setEmployees(d.employees);
      })
      .catch(console.error);
  }, []);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastStreamActivityRef = useRef<number>(0);
  const streamWatchdogFiredRef = useRef(false);
  const applyConversationState = useCallback((nextConversations: ChatConversation[], preferredId?: string | null) => {
    if (nextConversations.length === 0) {
      const fresh = createConversation();
      setConversations([fresh]);
      setActiveId(fresh.id);
      return;
    }

    setConversations(nextConversations);
    setActiveId((current) => {
      const desiredId = preferredId ?? current;
      return desiredId && nextConversations.some((conversation) => conversation.id === desiredId)
        ? desiredId
        : nextConversations[0].id;
    });
  }, []);

  const syncStoredHistory = useCallback(
    async (sourceConversations: ChatConversation[], label = "Syncing history…") => {
      const pendingDeletes = loadPendingDeletes();
      const conversationsToSync = sourceConversations.filter(
        (conversation) => conversation.messages.length > 0 && !pendingDeletes.includes(conversation.id)
      );

      if (pendingDeletes.length === 0 && conversationsToSync.length === 0) {
        setSyncStatus({ kind: "synced", label: "Synced" });
        return;
      }

      setSyncStatus({ kind: "syncing", label });

      const remainingDeletes: string[] = [];
      let hadSyncError = false;

      for (const conversationId of pendingDeletes) {
        try {
          await removeChatConversation(conversationId);
        } catch {
          hadSyncError = true;
          remainingDeletes.push(conversationId);
        }
      }

      savePendingDeletes(remainingDeletes);

      for (const conversation of conversationsToSync) {
        try {
          await upsertChatConversation(conversation);
        } catch {
          hadSyncError = true;
        }
      }

      setSyncStatus(
        hadSyncError
          ? { kind: "local", label: "Offline (Local only)" }
          : { kind: "synced", label: "Synced" }
      );
    },
    []
  );

  /* Load from localStorage on mount, then reconcile with backend */
  useEffect(() => {
    const pendingDeletes = loadPendingDeletes();
    const localConversations = loadConversations().filter(
      (conversation) => !pendingDeletes.includes(conversation.id)
    );

    applyConversationState(localConversations);
    if (localConversations.length > 0 || pendingDeletes.length > 0) {
      setSyncStatus({ kind: "local", label: "Syncing cached history…" });
    }

    let cancelled = false;

    const hydrateFromBackend = async () => {
      try {
        setSyncStatus({ kind: "syncing", label: "Syncing history…" });
        const remoteConversations = (await listChatConversations()).filter(
          (conversation) => !pendingDeletes.includes(conversation.id)
        );
        if (cancelled) return;

        const mergedConversations = mergeConversations(remoteConversations, localConversations);
        applyConversationState(mergedConversations);
        await syncStoredHistory(mergedConversations);
      } catch {
        if (!cancelled) {
          setSyncStatus({ kind: "local", label: "Offline (Local only)" });
        }
      }
    };

    void hydrateFromBackend();

    return () => {
      cancelled = true;
    };
  }, [applyConversationState, syncStoredHistory]);

  useEffect(() => {
    const handleOnline = () => {
      void syncStoredHistory(conversations, "Back online — syncing…");
    };
    const handleOffline = () => {
      setSyncStatus({ kind: "local", label: "Offline (Local only)" });
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [conversations, syncStoredHistory]);

  /* Persist whenever conversations change */
  useEffect(() => {
    if (conversations.length > 0) {
      const result = saveConversations(conversations);
      if (!result.success) {
        setStorageWarning("Local storage limit reached. Chat history could not be saved.");
      } else if (result.prunedCount > 0) {
        setStorageWarning(`Local storage limit reached. Oldest ${result.prunedCount} chat(s) were pruned to save space.`);
        const prunedList = conversations.slice(0, conversations.length - result.prunedCount);
        applyConversationState(prunedList);
      }
    }
  }, [conversations, applyConversationState]);

  const activeConv = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId) ?? null,
    [conversations, activeId]
  );
  const messages = useMemo(() => activeConv?.messages ?? [], [activeConv]);

  /* Auto-scroll */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);
  useEffect(scrollToBottom, [messages, status, scrollToBottom]);

  /* Conversation mutators */
  const updateActiveMessages = useCallback(
    (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
      setConversations((convs) =>
        convs.map((c) =>
          c.id === activeId
            ? { ...c, messages: updater(c.messages), updatedAt: Date.now() }
            : c
        )
      );
    },
    [activeId]
  );

  const setActiveTitle = useCallback(
    (title: string) => {
      setConversations((convs) =>
        convs.map((c) => (c.id === activeId ? { ...c, title } : c))
      );
    },
    [activeId]
  );

  /* New / switch / delete chat */
  const startNewChat = useCallback(() => {
    if (status.kind !== "idle") return;
    const fresh = createConversation();
    setConversations((prev) => [fresh, ...prev]);
    setActiveId(fresh.id);
    setInput("");
    setHistoryOpen(false);
    setCompletedNodes([]);
  }, [status.kind]);

  const confirmEscalate = useCallback(async (msgIndex: number, assigneeName?: string) => {
    const aiMsg = messages[msgIndex];
    if (!aiMsg || aiMsg.role !== "assistant") return;
    
    let query = "No query explicitly found for this response.";
    for (let i = msgIndex - 1; i >= 0; i--) {
       if (messages[i].role === "user") {
           query = messages[i].content;
           break;
       }
    }
    const summary = messages.slice(0, msgIndex + 1).map((m) => `${m.role.toUpperCase()}: ${m.content}`).join("\n").slice(-2500);

    try {
      setEscalatingMsgId(null);
      const res = await fetch("/api/escalate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, summary: summary, assignee_name: assigneeName }),
      });
      if (!res.ok) {
        const err = await res.json();
        alert(`Escalation failed: ${err.error || "Unknown error"}`);
      } else {
        alert("Conversation escalated to Slack successfully!");
        // Refresh employees to bump issue counts
        fetch("/api/employees", { cache: "no-store", headers: { "Cache-Control": "no-cache" } })
          .then(r => r.json())
          .then(d => { if (d.employees) setEmployees(d.employees); })
          .catch(console.error);
      }
    } catch {
      alert("Error escalating conversation.");
    }
  }, [messages]);

  const switchChat = useCallback(
    (id: string) => {
      if (status.kind !== "idle") return;
      setActiveId(id);
      setHistoryOpen(false);
      setCompletedNodes([]);
    },
    [status.kind]
  );

  const deleteChat = useCallback(
    (id: string) => {
      queuePendingDelete(id);
      setConversations((prev) => {
        const filtered = prev.filter((c) => c.id !== id);
        if (filtered.length === 0) {
          const fresh = createConversation();
          setActiveId(fresh.id);
          return [fresh];
        }
        if (id === activeId) setActiveId(filtered[0].id);
        return filtered;
      });
      void removeChatConversation(id)
        .then(() => {
          clearPendingDelete(id);
          setSyncStatus({ kind: "synced", label: "Synced" });
        })
        .catch(() => {
          setSyncStatus({ kind: "local", label: "Offline (Delete pending)" });
        });
    },
    [activeId]
  );

  /* ─── Send message & consume SSE stream ─── */
  const sendMessage = useCallback(async () => {
    const userMsg = input.trim();
    if (!userMsg || status.kind !== "idle" || !activeId || !activeConv) return;

    const now = Date.now();
    const assistantTimestamp = now + 1;
    const conversationTitle = messages.length === 0 ? deriveTitle(userMsg) : activeConv.title;
    const createdAt = activeConv.createdAt || now;
    const userMessage: ChatMessage = {
      role: "user",
      content: userMsg,
      timestamp: now,
    };
    let assistantContent = "";
    let assistantIntent: string | null = null;
    let shouldPersistAssistant = false;

    setInput("");
    setCompletedNodes([]);

    if (messages.length === 0) setActiveTitle(conversationTitle);

    updateActiveMessages((prev) => [
      ...prev,
      userMessage,
      { role: "assistant", content: "", timestamp: assistantTimestamp },
    ]);
    setSyncStatus({ kind: "syncing", label: "Saving chat…" });
    void appendChatMessage(activeId, conversationTitle, userMessage, {
      createdAt,
      updatedAt: now,
    })
      .then(() => {
        setSyncStatus({ kind: "synced", label: "Synced" });
      })
      .catch(() => {
        setSyncStatus({ kind: "local", label: "Offline (Local only)" });
      });

    setStatus({ kind: "connecting" });
    streamWatchdogFiredRef.current = false;
    lastStreamActivityRef.current = Date.now();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const params = new URLSearchParams({
        "input-query": userMsg,
        "thread-id": activeId,
      });

      const token = typeof window !== "undefined" ? localStorage.getItem("profit_pilot_token") : null;
      const res = await fetch(`/api/chat?${params.toString()}`, {
        method: "POST",
        signal: ctrl.signal,
        headers: {
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok || !res.body) {
        const errText = await res.text().catch(() => "Unknown error");
        throw new Error(`HTTP ${res.status}: ${errText}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const jsonStr = line.slice(6);
            if (!jsonStr) continue;

            try {
              const evt = JSON.parse(jsonStr);
              lastStreamActivityRef.current = Date.now();
              switch (evt.type) {
                case "chain_start":
                  break;
                case "chain_step_complete":
                  break;
                case "node_status": {
                  const nodeName = (evt.node as string) || "";
                  const msg = (evt.message as string) || "";
                  if (msg) setStatus({ kind: "streaming", label: msg, node: nodeName });
                  break;
                }
                case "status": {
                  const nodeName = evt.node || "";
                  setStatus({ kind: "streaming", label: evt.status, node: nodeName });
                  if (nodeName && nodeName !== "__start__") {
                    setCompletedNodes((prev) => {
                      if (prev.some((n) => n.name === nodeName)) return prev;
                      return [...prev, { name: nodeName, friendlyName: friendlyNodeName(nodeName) }];
                    });
                  }
                  break;
                }
                case "token":
                  assistantContent += evt.content;
                  updateActiveMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = {
                        ...last,
                        content: last.content + evt.content,
                      };
                    }
                    return updated;
                  });
                  break;

                case "clarification":
                  assistantContent = evt.clarification;
                  assistantIntent = evt.intent_str ?? null;
                  shouldPersistAssistant = true;
                  updateActiveMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = {
                        ...last,
                        content: evt.clarification,
                        intent: evt.intent_str,
                      };
                    }
                    return updated;
                  });
                  setStatus({ kind: "clarification", text: evt.clarification });
                  break;

                case "final":
                  assistantIntent = evt.intent_str ?? null;
                  shouldPersistAssistant = assistantContent.trim().length > 0;
                  updateActiveMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      updated[updated.length - 1] = { ...last, intent: evt.intent_str };
                    }
                    return updated;
                  });
                  setStatus({ kind: "idle" });
                  break;

                case "error":
                  shouldPersistAssistant = false;
                  updateActiveMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                      const nextContent = last.content || `⚠ Error: ${evt.error}`;
                      assistantContent = nextContent;
                      updated[updated.length - 1] = {
                        ...last,
                        content: nextContent,
                      };
                    }
                    return updated;
                  });
                  setStatus({ kind: "idle" });
                  break;
              }
            } catch { /* skip malformed */ }
          }
        }
      }

      if (shouldPersistAssistant && assistantContent.trim()) {
        setSyncStatus({ kind: "syncing", label: "Syncing reply…" });
        await upsertChatConversation({
          id: activeId,
          title: conversationTitle,
          createdAt,
          updatedAt: Math.max(assistantTimestamp, Date.now()),
          messages: [
            ...messages,
            userMessage,
            {
              role: "assistant",
              content: assistantContent,
              intent: assistantIntent,
              timestamp: assistantTimestamp,
            },
          ],
        });
        setSyncStatus({ kind: "synced", label: "Synced" });
      }

      setStatus((cur) => (cur.kind === "idle" ? cur : { kind: "idle" }));
    } catch (err: unknown) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        const errMsg = err instanceof Error ? err.message : "Unknown error";
        updateActiveMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: last.content || `Error: Could not reach the AI agent. ${errMsg}`,
            };
            assistantContent = updated[updated.length - 1].content;
          }
          return updated;
        });
        setSyncStatus({ kind: "local", label: "Offline (Local only)" });
      }
      setStatus({ kind: "idle" });
    } finally {
      abortRef.current = null;
    }
  }, [input, status.kind, activeId, activeConv, messages, updateActiveMessages, setActiveTitle]);

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    setStatus({ kind: "idle" });
  }, []);

  const isBusy = status.kind !== "idle";

  /* Stale-stream UX: no SSE progress → warn at 10s / 15s, abort + error at 30s */
  useEffect(() => {
    if (!isBusy) return;
    const tick = () => {
      const idle = Date.now() - lastStreamActivityRef.current;
      if (idle > 30_000 && !streamWatchdogFiredRef.current) {
        streamWatchdogFiredRef.current = true;
        abortRef.current?.abort();
        updateActiveMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content:
                last.content ||
                "❌ Request timed out. Please try again or rephrase your question.",
            };
          }
          return updated;
        });
        setStatus({ kind: "idle" });
        return;
      }
      if (idle > 15_000) {
        setStatus((cur) =>
          cur.kind === "streaming" || cur.kind === "connecting"
            ? {
                kind: "streaming",
                label: "⚠️ This is taking longer than usual. Still working…",
                node: cur.kind === "streaming" ? cur.node : undefined,
              }
            : cur
        );
      } else if (idle > 10_000) {
        setStatus((cur) =>
          cur.kind === "streaming" || cur.kind === "connecting"
            ? {
                kind: "streaming",
                label: "⚠️ Taking longer than expected…",
                node: cur.kind === "streaming" ? cur.node : undefined,
              }
            : cur
        );
      }
    };
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [isBusy, updateActiveMessages]);

  const statusLabel = useMemo(() => {
    switch (status.kind) {
      case "connecting": return "Connecting…";
      case "streaming": return status.label;
      case "clarification": return "Waiting for your response…";
      default: return null;
    }
  }, [status]);

  const relativeTime = (ts: number) => {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-area">
        <Topbar onSearch={() => { }} />
        <div className="content-wrapper" style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 69px)", padding: 0 }}>
          {storageWarning && (
            <div style={{
              background: "#fee2e2",
              borderBottom: "1px solid #fca5a5",
              color: "#991b1b",
              padding: "10px 16px",
              fontSize: "13px",
              fontWeight: 500,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center"
            }}>
              <span>⚠️ {storageWarning}</span>
              <button
                onClick={() => setStorageWarning(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#991b1b",
                  fontWeight: "bold",
                  fontSize: "14px",
                  cursor: "pointer",
                  padding: "2px 6px"
                }}
              >
                ✕
              </button>
            </div>
          )}

          {/* ── Chat Header ── */}
          <div className="chat-header">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h2 className="chat-header-title">
                <ChatbotIcon size={20} color="var(--accent-blue)" /> AI Business Agent
              </h2>
              <div style={{ display: "flex", gap: 8 }}>

                <button className="chat-header-btn" onClick={() => setHistoryOpen(!historyOpen)} title="Chat history">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                  History
                </button>
                <button className="chat-header-btn primary" onClick={startNewChat} disabled={isBusy} title="New chat">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  New Chat
                </button>
              </div>
            </div>
            <p className="chat-header-subtitle">
              Ask questions about your business data, financials, employees, and more.
              {process.env.NEXT_PUBLIC_SLACK_APP_URL ? (
                <>
                  {" "}
                  <a
                    href={process.env.NEXT_PUBLIC_SLACK_APP_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="chat-slack-link"
                  >
                    Open in Slack
                  </a>
                </>
              ) : null}
            </p>
            <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: syncStatus.kind === "local" ? "#b45309" : "#475569",
                  background: syncStatus.kind === "local" ? "rgba(245, 158, 11, 0.12)" : "rgba(148, 163, 184, 0.12)",
                  borderRadius: "999px",
                  padding: "4px 10px",
                }}
              >
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "999px",
                    background:
                      syncStatus.kind === "synced"
                        ? "#16a34a"
                        : syncStatus.kind === "syncing" || syncStatus.kind === "loading"
                          ? "#2563eb"
                          : "#f59e0b",
                  }}
                />
                {syncStatus.label}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", flex: 1, overflow: "hidden", position: "relative" }}>

            {/* ── History Panel ── */}
            {historyOpen && (
              <div className="chat-history-panel">
                <div className="chat-history-header">
                  <span className="chat-history-title">Chat History</span>
                  <button className="chat-history-close" onClick={() => setHistoryOpen(false)}>✕</button>
                </div>
                <div className="chat-history-list">
                  {conversations.map((conv) => (
                    <div key={conv.id} className={`chat-history-item ${conv.id === activeId ? "active" : ""}`} onClick={() => switchChat(conv.id)}>
                      <div className="chat-history-item-title">{conv.title}</div>
                      <div className="chat-history-item-meta">{conv.messages.length} messages · {relativeTime(conv.updatedAt)}</div>
                      <button className="chat-history-delete" onClick={(e) => { e.stopPropagation(); deleteChat(conv.id); }} title="Delete">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Messages ── */}
            <div className="chat-messages" style={{ flex: 1 }}>
              {messages.length === 0 && (
                <div className="chat-empty">
                  <div className="chat-empty-icon"><ChatbotIcon size={48} color="var(--accent-blue)" /></div>
                  <p className="chat-empty-title">Hello! I&apos;m your AI Business Agent.</p>
                  <p>Ask me anything about your business data.</p>
                  <div className="chat-suggestions">
                    {["What was last month's revenue?", "Show me top selling products", "How many employees do we have?", "Show application error logs"].map((s) => (
                      <button key={s} className="chat-suggestion-chip" onClick={() => setInput(s)}>{s}</button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} className={`chat-bubble-row ${msg.role === "user" ? "user" : "assistant"}`}>
                  {msg.role === "assistant" && (
                    <div className="chat-avatar assistant-avatar"><ChatbotIcon size={16} color="white" /></div>
                  )}
                  <div className={`chat-bubble ${msg.role === "user" ? "user-bubble" : "assistant-bubble"}`}>
                    {msg.content ? (
                      msg.role === "assistant" ? (
                        <>
                          <MessageRenderer
                            content={msg.content}
                            intent={msg.intent ?? undefined}
                            onFollowUpClick={(q) => {
                              setInput(q);
                              setTimeout(() => {
                                const btn = document.getElementById("chat-send-btn") as HTMLButtonElement | null;
                                btn?.click();
                              }, 50);
                            }}
                          />
                          {!msg.content.startsWith("⚠ Error:") && !isBusy && (
                            <div style={{ marginTop: "12px", borderTop: "1px solid rgba(0,0,0,0.05)", paddingTop: "8px" }}>
                              {escalatingMsgId === i ? (
                                <div style={{ padding: "12px", background: "white", border: "1px solid rgba(0,0,0,0.08)", borderRadius: "8px", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
                                  <div style={{ fontSize: "12px", fontWeight: 600, marginBottom: "12px", color: "var(--text-main)" }}>Assign Issue To:</div>
                                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "8px", maxHeight: "180px", overflowY: "auto", paddingRight: "4px" }}>
                                    {employees.map(emp => (
                                      <button 
                                        key={emp.login} 
                                        onClick={() => confirmEscalate(i, emp.login)}
                                        style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "6px", background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "8px", padding: "10px", cursor: "pointer", transition: "all 0.2s" }}
                                        onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--accent-orange, #f97316)"; e.currentTarget.style.background = "rgba(249,115,22,0.02)"; }}
                                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e5e7eb"; e.currentTarget.style.background = "#f9fafb"; }}
                                      >
                                        {emp.avatar_url ? (
                                          <img src={emp.avatar_url} alt={emp.login} style={{ width: "32px", height: "32px", borderRadius: "50%", objectFit: "cover" }} />
                                        ) : (
                                          <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#ddd", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", fontWeight: "bold", color: "#666" }}>
                                            {emp.login.charAt(0).toUpperCase()}
                                          </div>
                                        )}
                                        <b style={{ color: "var(--text-main)", fontSize: "12px", maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{emp.login}</b>
                                        <span style={{ background: "rgba(249,115,22,0.1)", color: "var(--accent-orange, #f97316)", padding: "2px 6px", borderRadius: "10px", fontSize: "10px", fontWeight: 600 }}>
                                          {emp.assigned_issues} issues
                                        </span>
                                      </button>
                                    ))}
                                  </div>
                                  <div style={{ marginTop: "12px", display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                                    <button
                                      onClick={() => confirmEscalate(i, undefined)}
                                      style={{ fontSize: "11px", padding: "6px 12px", cursor: "pointer", background: "var(--accent-blue)", color: "white", border: "none", borderRadius: "6px", fontWeight: 500 }}
                                    >
                                      Slack Auto-Assignment
                                    </button>
                                    <button
                                      onClick={() => setEscalatingMsgId(null)}
                                      style={{ fontSize: "11px", padding: "6px 12px", cursor: "pointer", background: "#f1f5f9", color: "#475569", border: "none", borderRadius: "6px", fontWeight: 500 }}
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <button 
                                  onClick={() => setEscalatingMsgId(i)}
                                  className="chat-btn"
                                  style={{
                                    fontSize: "12px",
                                    padding: "4px 8px",
                                    borderRadius: "4px",
                                    backgroundColor: "transparent",
                                    border: "1px solid var(--accent-orange, #f97316)",
                                    color: "var(--accent-orange, #f97316)",
                                    cursor: "pointer",
                                    display: "inline-flex",
                                    alignItems: "center",
                                    gap: "4px"
                                  }}
                                  title="Escalate this issue to a human via Slack"
                                >
                                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>
                                  Escalate to Slack
                                </button>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        msg.content
                      )
                    ) : (
                      <span className="chat-thinking-dots"><span /><span /><span /></span>
                    )}
                    {msg.intent && <span className="chat-intent-badge">{msg.intent}</span>}
                  </div>
                  {msg.role === "user" && <div className="chat-avatar user-avatar">U</div>}
                </div>
              ))}

              {/* ── Agent Flow Pipeline ── */}
              {isBusy && completedNodes.length > 0 && (
                <div className="agent-flow-bar">
                  <div className="agent-flow-label">Agent Flow</div>
                  <div className="agent-flow-pipeline">
                    {completedNodes.map((node, idx) => {
                      const isLast = idx === completedNodes.length - 1;
                      const isActive = isLast && status.kind === "streaming";
                      return (
                        <div key={node.name} className="agent-flow-step-wrapper">
                          {idx > 0 && <div className="agent-flow-connector" />}
                          <div className={`agent-flow-step ${isActive ? "active" : "done"}`}>
                            {isActive ? (
                              <span className="agent-flow-spinner" />
                            ) : (
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                            )}
                            <span>{node.friendlyName}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Status pill */}
              {statusLabel && (
                <div className="chat-status-bar">
                  <div className="chat-status-pill">
                    <span className="chat-status-dot" />{statusLabel}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* ── Input Area ── */}
          <div className="chat-input-area">
            <input id="chat-input" type="text" placeholder="Type your message…" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendMessage()} disabled={isBusy} className="chat-input" />
            {isBusy ? (
              <button id="chat-cancel-btn" onClick={cancelStream} className="chat-btn cancel-btn">Stop</button>
            ) : (
              <button id="chat-send-btn" onClick={sendMessage} disabled={!input.trim()} className="chat-btn send-btn">Send</button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
