import { renderSafeMarkdown } from './markdown.js';

// ── DOM references ─────────────────────────────────────────────
export const conversationList    = document.getElementById("conversationList");
export const noConversations     = document.getElementById("noConversations");
export const chatMessages        = document.getElementById("chatMessages");
export const welcomeScreen       = document.getElementById("welcomeScreen");
export const chatInput           = document.getElementById("chatInput");
export const btnSend             = document.getElementById("btnSend");
export const btnNewChat          = document.getElementById("btnNewChat");
export const chatSidebar         = document.getElementById("chatSidebar");
export const chatSidebarToggle   = document.getElementById("chatSidebarToggle");

// ── Configurations ─────────────────────────────────────────────
const INTENT_META = {
    database_request:            { label: "Database Agent",      icon: "fa-database",       color: "#5b8af5" },
    general_information_request: { label: "General Info Agent",   icon: "fa-circle-info",    color: "#a855f7" },
    greeting_request:            { label: "Greeting Agent",       icon: "fa-hand-wave",      color: "#4ecb71" },
    logs_request:                { label: "Logs Agent",           icon: "fa-file-lines",     color: "#f5a623" },
    metrics_request:             { label: "Metrics Agent",        icon: "fa-gauge-high",     color: "#22d3ee" },
};

const RISK_CONFIG = {
    low:    { bg: "#d1fae5", text: "#065f46", border: "#6ee7b7", emoji: "🟢" },
    medium: { bg: "#fef3c7", text: "#92400e", border: "#fcd34d", emoji: "🟡" },
    high:   { bg: "#fee2e2", text: "#991b1b", border: "#fca5a5", emoji: "🔴" },
};

const BORDER_COLORS = {
    success: "#6366f1", advisory: "#3b82f6", hybrid: "#3b82f6",
    error: "#ef4444", partial: "#f59e0b", database: "#6366f1",
};

const SIMPLE_STATUSES = new Set(["greeting", "out_of_scope", "greeting_request"]);

// ── Callback Injection (The Trick) ─────────────────────────────
// This allows ui.js to ask chatbot.js to send a message without importing it directly
let onSendMessageCallback = null;
export function setOnSendMessageCallback(callback) {
    onSendMessageCallback = callback;
}

// ── UI Helpers ─────────────────────────────────────────────────
export function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

export function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

export function autoResizeInput() {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
}

export function closeMobileSidebar() {
    if (chatSidebar) chatSidebar.classList.remove("open");
}

export function showWelcome() {
    chatMessages.innerHTML = "";
    if (welcomeScreen) {
        const clone = welcomeScreen.cloneNode(true);
        clone.style.display = "flex";
        chatMessages.appendChild(clone);
        // Note: the clone relies on the global window.sendSuggestion defined in chatbot.js
    }
}

export function highlightActiveConv(activeConversationId) {
    conversationList.querySelectorAll(".conv-item").forEach((el) => {
        el.classList.toggle("active", el.dataset.id === activeConversationId);
    });
}

export function buildIntentBadges(intentStr) {
    if (!intentStr) return "";
    const intents = intentStr.split(",").map((s) => s.trim()).filter(Boolean);
    if (intents.length === 0) return "";

    return `<div class="intent-badges">${intents.map((intent) => {
        const meta = INTENT_META[intent] || { label: intent, icon: "fa-robot", color: "#9ea2b8" };
        return `<span class="intent-badge" style="--intent-color: ${meta.color}">
                    <i class="fas ${meta.icon}"></i>
                    <span>${meta.label}</span>
                </span>`;
    }).join("")}</div>`;
}

// ── Primary Rendering Functions ────────────────────────────────
export function renderMessageContent(container, rawText) {
    let parsed = null;
    if (typeof rawText === "string" && rawText.trimStart().startsWith("{")) {
        try { parsed = JSON.parse(rawText); } catch { /* not JSON */ }
    }

    if (!parsed) {
        renderSafeMarkdown(container, rawText);
        return;
    }

    const status  = (parsed.status  || parsed.intent || "success").toLowerCase();
    const summary = parsed.summary  || (parsed.result && parsed.result.summary) || "";
    const recs    = Array.isArray(parsed.recommendations) ? parsed.recommendations : (parsed.result && Array.isArray(parsed.result.recommendations) ? parsed.result.recommendations : []);
    const riskRaw = ((parsed.risk_level || (parsed.result && parsed.result.risk_level) || "")).toString().toLowerCase().trim();
    const followUps = Array.isArray(parsed.follow_up_questions) ? parsed.follow_up_questions : [];
    const queryUnderstood = parsed.query_understood || "";

    if (SIMPLE_STATUSES.has(status)) {
        renderSafeMarkdown(container, summary || rawText);
        return;
    }

    const card = document.createElement("div");
    card.className = "biz-response-card";
    card.style.borderLeftColor = BORDER_COLORS[status] || "#6366f1";

    if (queryUnderstood) {
        const qu = document.createElement("div");
        qu.className = "biz-query-understood";
        qu.innerHTML = `<span class="biz-section-icon">🧠</span><span>${escapeHtml(queryUnderstood)}</span>`;
        card.appendChild(qu);
    }
    if (summary) {
        const s = document.createElement("div");
        s.className = "biz-summary";
        const icon = document.createElement("span");
        icon.className = "biz-section-icon";
        icon.textContent = "📋";
        const text = document.createElement("div");
        text.className = "biz-summary-text";
        renderSafeMarkdown(text, summary);
        s.appendChild(icon);
        s.appendChild(text);
        card.appendChild(s);
    }
    if (recs.length > 0) {
        const section = document.createElement("div");
        section.className = "biz-section";
        const title = document.createElement("div");
        title.className = "biz-section-title";
        title.innerHTML = `<span class="biz-section-icon">💡</span> Recommendations`;
        const ul = document.createElement("ul");
        ul.className = "biz-list";
        recs.forEach((rec) => {
            const li = document.createElement("li");
            li.textContent = rec;
            ul.appendChild(li);
        });
        section.appendChild(title);
        section.appendChild(ul);
        card.appendChild(section);
    }
    const riskStyle = RISK_CONFIG[riskRaw];
    if (riskStyle) {
        const row = document.createElement("div");
        row.className = "biz-risk-row";
        row.innerHTML = `
            <span class="biz-risk-label">⚠️ Risk Level</span>
            <span class="biz-risk-badge" style="background:${riskStyle.bg};color:${riskStyle.text};border:1px solid ${riskStyle.border}">
              ${riskStyle.emoji} ${riskRaw.toUpperCase()}
            </span>`;
        card.appendChild(row);
    }
    if (followUps.length > 0) {
        const fu = document.createElement("div");
        fu.className = "biz-followups";
        const fuTitle = document.createElement("div");
        fuTitle.className = "biz-followups-title";
        fuTitle.textContent = "❓ You might also ask:";
        fu.appendChild(fuTitle);
        const chips = document.createElement("div");
        chips.className = "biz-followup-chips";
        followUps.forEach((q) => {
            const chip = document.createElement("button");
            chip.className = "biz-followup-chip";
            chip.innerHTML = `<span class="biz-followup-arrow">→</span> ${escapeHtml(q)}`;
            chip.title = q;
            chip.addEventListener("click", () => {
                chatInput.value = q;
                autoResizeInput();
                // Instead of calling sendMessage() directly, we use the callback
                if (onSendMessageCallback) onSendMessageCallback(q);
            });
            chips.appendChild(chip);
        });
        fu.appendChild(chips);
        card.appendChild(fu);
    }
    if (status === "partial") {
        const note = document.createElement("div");
        note.className = "biz-partial-note";
        note.textContent = "⚠️ This is a partial result — try rephrasing for a complete answer.";
        card.appendChild(note);
    }
    container.appendChild(card);
}

export function appendStreamMessage(role, timestamp) {
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;

    const avatar = role === "user" ? "U" : '<i class="fas fa-robot"></i>';
    const timeStr = timestamp
        ? new Date(timestamp + "Z").toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        : new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

    bubble.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-body">
            <div class="dynamic-intents"></div>
            <div class="agent-status" style="font-size:0.8em;color:#888;font-style:italic;margin-bottom:5px;"></div>
            <div class="message-content"></div>
            <div class="message-time">${timeStr}</div>
        </div>
    `;
    chatMessages.appendChild(bubble);
    scrollToBottom();
    
    return {
        updateContent: (text) => {
            const contentDiv = bubble.querySelector(".message-content");
            contentDiv.innerHTML = "";
            renderMessageContent(contentDiv, text);
            scrollToBottom();
        },
        updateIntents: (intentStr) => {
            bubble.querySelector(".dynamic-intents").innerHTML = buildIntentBadges(intentStr);
        },
        updateStatus: (statusText) => {
            const statusDiv = bubble.querySelector(".agent-status");
            if (statusText) {
                statusDiv.style.display = "block";
                statusDiv.innerHTML = '<i class="fas fa-circle-notch fa-spin" style="margin-right:5px;"></i>' + escapeHtml(statusText);
            } else {
                statusDiv.style.display = "none";
            }
            scrollToBottom();
        }
    };
}

export function appendMessage(role, content, timestamp, intentStr) {
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;

    const avatar = role === "user" ? "U" : '<i class="fas fa-robot"></i>';
    const timeStr = timestamp
        ? new Date(timestamp + "Z").toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        : new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

    const intentHtml = (role === "assistant") ? buildIntentBadges(intentStr) : "";

    bubble.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-body">
            ${intentHtml}
            <div class="message-content"></div>
            <div class="message-time">${timeStr}</div>
        </div>
    `;

    const contentDiv = bubble.querySelector(".message-content");
    if (role === "assistant") {
        renderMessageContent(contentDiv, content);
    } else {
        contentDiv.textContent = content;
    }

    chatMessages.appendChild(bubble);
    scrollToBottom();
}

export function showTypingIndicator() {
    const el = document.createElement("div");
    el.className = "message-bubble assistant";
    el.id = "typingIndicator";
    el.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-body">
            <div class="intent-badges">
                <span class="intent-badge processing" style="--intent-color: #5b8af5">
                    <i class="fas fa-spinner fa-spin"></i>
                    <span>Processing with Agent...</span>
                    <span class="intent-flow-indicator active"></span>
                </span>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
    return el;
}