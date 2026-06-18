/* ──────────────────────────────────────────────────────────────────
   chatbot.js – Conversation Management & Controller
   This is the entry point. It handles state, URLs, and streaming.
   ────────────────────────────────────────────────────────────────── */

// 1. IMPORTING MODULES
import { api } from "./api.js";
import * as ui from "./ui.js"; // Imports all DOM variables and rendering functions

// 2. STATE MANAGEMENT
let activeConversationId = null;
let isSending = false;

// 3. INJECT CALLBACK INTO UI (Solves the circular dependency)
ui.setOnSendMessageCallback(sendMessage);

// ── URL helpers ────────────────────────────────────────────────
function pushConversationUrl(convId) {
    if (convId) {
        window.history.pushState({ convId }, "", `/chatbot/${convId}`);
    } else {
        window.history.pushState({}, "", `/chatbot`);
    }
}

function getConversationIdFromUrl() {
    const m = window.location.pathname.match(/\/chatbot\/([0-9a-f-]{36})/i);
    return m ? m[1] : null;
}

// Handle browser back/forward
window.addEventListener("popstate", (e) => {
    const convId = getConversationIdFromUrl();
    if (convId) {
        selectConversation(convId, false);
    } else {
        activeConversationId = null;
        ui.showWelcome();
        ui.highlightActiveConv(activeConversationId);
    }
});

// ── Conversation List ──────────────────────────────────────────
async function loadConversations() {
    const data = await api("/api/chat/conversations");
    if (!data) return;

    // Clear existing items using UI DOM references
    const items = ui.conversationList.querySelectorAll(".conv-item");
    items.forEach((el) => el.remove());

    if (data.length === 0) {
        ui.noConversations.style.display = "block";
        return;
    }
    ui.noConversations.style.display = "none";

    data.forEach((conv) => {
        const el = document.createElement("div");
        el.className = "conv-item" + (conv.conversation_id === activeConversationId ? " active" : "");
        el.dataset.id = conv.conversation_id;

        const dateStr = conv.updated_at
            ? new Date(conv.updated_at + "Z").toLocaleString("en-US", {
                  month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
              })
            : "";

        el.innerHTML = `
            <div class="conv-item-info">
                <div class="conv-item-title">${ui.escapeHtml(conv.title)}</div>
                <div class="conv-item-date">${dateStr}</div>
            </div>
            <button class="conv-item-delete" title="Delete conversation">
                <i class="fas fa-trash"></i>
            </button>
        `;

        el.querySelector(".conv-item-info").addEventListener("click", () => {
            selectConversation(conv.conversation_id);
        });

        el.querySelector(".conv-item-delete").addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm("Delete this conversation?")) return;
            await api(`/api/chat/conversations/${conv.conversation_id}`, { method: "DELETE" });
            if (activeConversationId === conv.conversation_id) {
                activeConversationId = null;
                ui.showWelcome();
                pushConversationUrl(null);
            }
            loadConversations();
        });

        ui.conversationList.appendChild(el);
    });
}

// ── Select / load conversation ─────────────────────────────────
async function selectConversation(convId, updateUrl = true) {
    activeConversationId = convId;
    ui.highlightActiveConv(activeConversationId);

    if (updateUrl) pushConversationUrl(convId);

    // Load messages
    const messages = await api(`/api/chat/conversations/${convId}/messages`);
    if (!messages) return;

    ui.chatMessages.innerHTML = "";
    if (messages.length === 0) {
        ui.showWelcome();
        return;
    }

    if (ui.welcomeScreen) ui.welcomeScreen.style.display = "none";
    
    messages.forEach((msg) => {
        ui.appendMessage(msg.role, msg.content, msg.created_at, msg.intent);
    });

    ui.scrollToBottom();
    ui.closeMobileSidebar();
}

// ── New chat ───────────────────────────────────────────────────
async function createNewChat() {
    const data = await api("/api/chat/conversations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Chat" }),
    });
    if (!data) return;

    activeConversationId = data.conversation_id;
    pushConversationUrl(data.conversation_id);
    ui.chatMessages.innerHTML = "";
    ui.showWelcome();
    await loadConversations();
    ui.closeMobileSidebar();
}

// ── Send message (Streaming Logic) ─────────────────────────────
async function sendMessage(text) {
    if (!text.trim() || isSending) return;

    // Auto-create conversation if none active
    if (!activeConversationId) {
        const data = await api("/api/chat/conversations", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: text.trim().substring(0, 50) }),
        });
        if (!data) return;
        activeConversationId = data.conversation_id;
        pushConversationUrl(data.conversation_id);
        await loadConversations();
    }

    // Hide welcome screen
    if (ui.welcomeScreen) ui.welcomeScreen.style.display = "none";

    // Show user message
    ui.appendMessage("user", text.trim());
    ui.chatInput.value = "";
    ui.autoResizeInput();

    // Show typing indicator with "processing" status
    const typingEl = ui.showTypingIndicator();

    isSending = true;
    ui.btnSend.disabled = true;

    // Send to API via Fetch to stream
    try {
        const resp = await fetch("/api/chat/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                conversation_id: activeConversationId,
                message: text.trim(),
            }),
        });

        typingEl.remove();

        if (!resp.ok) {
            ui.appendMessage("assistant", "Sorry, an error occurred communicating with the server.");
            isSending = false;
            ui.btnSend.disabled = false;
            return;
        }

        const streamBubble = ui.appendStreamMessage("assistant");
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = "";
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop() || ""; // keep partial chunk
            
            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const payload = line.substring(6);
                    try {
                        const chunkData = JSON.parse(payload);
                        if (chunkData.type === "token") {
                            accumulatedContent += chunkData.content || "";
                            streamBubble.updateContent(accumulatedContent);
                        } else if (chunkData.type === "status") {
                            streamBubble.updateStatus(chunkData.status);
                        } else if (chunkData.type === "final") {
                            if (chunkData.content) {
                                accumulatedContent = chunkData.content;
                                streamBubble.updateContent(accumulatedContent);
                            }
                            streamBubble.updateIntents(chunkData.intent_str);
                            streamBubble.updateStatus("");
                        } else if (chunkData.type === "clarification") {
                            const clarif = chunkData.clarification;
                            accumulatedContent = typeof clarif === "string" ? clarif : (clarif.message || "Please clarify");
                            streamBubble.updateContent(accumulatedContent);
                            streamBubble.updateIntents(chunkData.intent_str);
                            streamBubble.updateStatus("");
                        } else if (chunkData.type === "error") {
                            accumulatedContent = "⚠️ Error: " + (chunkData.error || "Unknown");
                            streamBubble.updateContent(accumulatedContent);
                            streamBubble.updateStatus("");
                        }
                    } catch(e) { /* ignore parse error for chunk */ }
                }
            }
        }

        // flush any remaining buffer
        if (buffer.startsWith("data: ")) {
             try {
                 const payload = buffer.substring(6);
                 const chunkData = JSON.parse(payload);
                 if (chunkData.type === "token") {
                     accumulatedContent += chunkData.content || "";
                     streamBubble.updateContent(accumulatedContent);
                 } else if (chunkData.type === "final") {
                     streamBubble.updateIntents(chunkData.intent_str);
                     streamBubble.updateStatus("");
                 }
             } catch(e) { }
        }

    } catch (err) {
        typingEl.remove();
        ui.appendMessage("assistant", "Sorry, I could not connect. Please try again.");
    }

    isSending = false;
    ui.btnSend.disabled = false;
    ui.scrollToBottom();
    loadConversations(); // refresh sidebar
}

/* =====================================================================
   REMOVED FUNCTIONS:
   The following functions were extracted and moved entirely to ui.js:
   - highlightActiveConv()
   - buildIntentBadges()
   - renderMessageContent()
   - appendStreamMessage()
   - appendMessage()
   - showTypingIndicator()
   - showWelcome()
   - scrollToBottom()
   - escapeHtml()
   - autoResizeInput()
   - closeMobileSidebar()
   ===================================================================== */

// ── Event listeners ────────────────────────────────────────────

// Note: We now prefix DOM elements with 'ui.' since they are imported
ui.btnNewChat.addEventListener("click", createNewChat);

ui.btnSend.addEventListener("click", () => sendMessage(ui.chatInput.value));

ui.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(ui.chatInput.value);
    }
});

ui.chatInput.addEventListener("input", ui.autoResizeInput);

if (ui.chatSidebarToggle) {
    ui.chatSidebarToggle.addEventListener("click", () => {
        ui.chatSidebar.classList.toggle("open");
    });
}

// ── Global: suggestion chip handler ────────────────────────────
// This must remain attached to the window so the HTML buttons can call it
window.sendSuggestion = function (chipEl) {
    const text = chipEl.textContent.trim();
    ui.chatInput.value = text;
    sendMessage(text);
};

// ── Init ───────────────────────────────────────────────────────
// Because this is an ES module, we don't need a self-invoking function
// Top-level await is supported in modern browsers, but for safety in older setups
// we wrap the initialization sequence.
(async function init() {
    await loadConversations();

    // If URL has a conversation UUID, auto-select it
    const urlConvId = getConversationIdFromUrl();
    if (urlConvId) {
        await selectConversation(urlConvId, false);
    }
})();