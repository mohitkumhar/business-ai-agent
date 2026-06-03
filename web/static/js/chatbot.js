/* ──────────────────────────────────────────────────────────────────
   chatbot.js – Conversation management & chat with the agent
   Shows conversation UUID in URL bar and displays agent intent badges.
   ────────────────────────────────────────────────────────────────── */

(function () {
    "use strict";

    // ── DOM references ─────────────────────────────────────────────
    const conversationList    = document.getElementById("conversationList");
    const noConversations     = document.getElementById("noConversations");
    const chatMessages        = document.getElementById("chatMessages");
    const welcomeScreen       = document.getElementById("welcomeScreen");
    const chatInput           = document.getElementById("chatInput");
    const btnSend             = document.getElementById("btnSend");
    const btnNewChat          = document.getElementById("btnNewChat");
    const chatSidebar         = document.getElementById("chatSidebar");
    const chatSidebarToggle   = document.getElementById("chatSidebarToggle");

    let activeConversationId  = null;
    let isSending             = false;

    // ── Intent display config ──────────────────────────────────────
    const INTENT_META = {
        database_request:            { label: "Database Agent",      icon: "fa-database",       color: "#5b8af5" },
        general_information_request: { label: "General Info Agent",   icon: "fa-circle-info",    color: "#a855f7" },
        greeting_request:            { label: "Greeting Agent",       icon: "fa-hand-wave",      color: "#4ecb71" },
        logs_request:                { label: "Logs Agent",           icon: "fa-file-lines",     color: "#f5a623" },
        metrics_request:             { label: "Metrics Agent",        icon: "fa-gauge-high",     color: "#22d3ee" },
    };

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
            selectConversation(convId, false); // false = don't push URL again
        } else {
            activeConversationId = null;
            showWelcome();
            highlightActiveConv();
        }
    });

    // ── API helpers ────────────────────────────────────────────────
    async function api(url, options = {}) {
        try {
            const resp = await fetch(url, options);
            if (!resp.ok) {
                let errorText;
                try {
                    errorText = await resp.text();
                } catch (_) {
                    errorText = "Unable to read error response";
                }
                throw { status: resp.status, message: errorText };
            }
            return await resp.json();
        } catch (err) {
            console.error("API error:", err);
            return null;
         }
    }
         

    // ── Conversation List ──────────────────────────────────────────
    async function loadConversations() {
        const data = await api("/api/chat/conversations");
        if (!data) return;

        // Clear existing items (keep the empty state element)
        const items = conversationList.querySelectorAll(".conv-item");
        items.forEach((el) => el.remove());

        if (data.length === 0) {
            noConversations.style.display = "block";
            return;
        }
        noConversations.style.display = "none";

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
                    <div class="conv-item-title">${escapeHtml(conv.title)}</div>
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
                    showWelcome();
                    pushConversationUrl(null);
                }
                loadConversations();
            });

            conversationList.appendChild(el);
        });
    }

    function highlightActiveConv() {
        conversationList.querySelectorAll(".conv-item").forEach((el) => {
            el.classList.toggle("active", el.dataset.id === activeConversationId);
        });
    }

    // ── Select / load conversation ─────────────────────────────────
    async function selectConversation(convId, updateUrl = true) {
        activeConversationId = convId;
        highlightActiveConv();

        if (updateUrl) pushConversationUrl(convId);

        // Load messages
        const messages = await api(`/api/chat/conversations/${convId}/messages`);
        if (!messages) return;

        chatMessages.innerHTML = "";
        if (messages.length === 0) {
            showWelcome();
            return;
        }

        welcomeScreen && (welcomeScreen.style.display = "none");
        messages.forEach((msg) => {
            appendMessage(msg.role, msg.content, msg.created_at, msg.intent);
        });

        scrollToBottom();
        closeMobileSidebar();
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
        chatMessages.innerHTML = "";
        showWelcome();
        await loadConversations();
        closeMobileSidebar();
    }

    // ── Send message ───────────────────────────────────────────────
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
        if (welcomeScreen) welcomeScreen.style.display = "none";

        // Show user message
        appendMessage("user", text.trim());
        chatInput.value = "";
        autoResizeInput();

        // Show typing indicator with "processing" status
        const typingEl = showTypingIndicator();

        isSending = true;
        btnSend.disabled = true;

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
                appendMessage("assistant", "Sorry, an error occurred communicating with the server.");
                isSending = false;
                btnSend.disabled = false;
                return;
            }

            const streamBubble = appendStreamMessage("assistant");
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
            appendMessage("assistant", "Sorry, I could not connect. Please try again.");
        }

        isSending = false;
        btnSend.disabled = false;
        scrollToBottom();
        loadConversations(); // refresh sidebar
    }

    // ── Intent badge builder ───────────────────────────────────────
    function buildIntentBadges(intentStr) {
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

    // ── DOM Helpers ────────────────────────────────────────────────
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
    const UNSAFE_MARKDOWN_SELECTORS = [
        "script", "style", "iframe", "object", "embed", "link", "meta",
        "base", "form", "input", "button", "textarea", "select",
    ].join(",");
    const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "poster", "xlink:href"]);

    function isSafeMarkdownUrl(value) {
        if (!value) return true;

        const normalized = value.trim().replace(/[\u0000-\u001f\u007f\s]+/g, "");
        if (!normalized) return true;
        if (normalized.startsWith("#") || normalized.startsWith("/") || normalized.startsWith("./") || normalized.startsWith("../")) {
            return true;
        }

        try {
            const url = new URL(normalized, window.location.origin);
            return ["http:", "https:", "mailto:", "tel:"].includes(url.protocol);
        } catch {
            return false;
        }
    }

    function sanitizeMarkdownFragment(fragment) {
        fragment.querySelectorAll(UNSAFE_MARKDOWN_SELECTORS).forEach((node) => node.remove());

        const walker = document.createTreeWalker(fragment, NodeFilter.SHOW_ELEMENT);
        const elements = [];
        let node = walker.nextNode();
        while (node) {
            elements.push(node);
            node = walker.nextNode();
        }

        elements.forEach((el) => {
            Array.from(el.attributes).forEach((attr) => {
                const name = attr.name.toLowerCase();
                if (name.startsWith("on") || name === "style" || name === "srcdoc") {
                    el.removeAttribute(attr.name);
                    return;
                }
                if (URL_ATTRIBUTES.has(name) && !isSafeMarkdownUrl(attr.value)) {
                    el.removeAttribute(attr.name);
                }
            });

            if (el.tagName.toLowerCase() === "a" && el.getAttribute("target") === "_blank") {
                el.setAttribute("rel", "noopener noreferrer");
            }
        });
    }

    function renderSafeMarkdown(container, markdownText) {
        let html = "";
        try {
            html = marked.parse(String(markdownText || ""));
        } catch {
            container.textContent = markdownText || "";
            return;
        }

        const template = document.createElement("template");
        template.innerHTML = html;
        sanitizeMarkdownFragment(template.content);
        container.replaceChildren(template.content);
    }

    /** Render assistant content into `container` — JSON card or plain markdown. */
    function renderMessageContent(container, rawText) {
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
        const recs    = Array.isArray(parsed.recommendations)
            ? parsed.recommendations
            : (parsed.result && Array.isArray(parsed.result.recommendations) ? parsed.result.recommendations : []);
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
                <span class="biz-risk-badge"
                      style="background:${riskStyle.bg};color:${riskStyle.text};border:1px solid ${riskStyle.border}">
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
                    sendMessage(q);
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

    function appendStreamMessage(role, timestamp) {
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

    function appendMessage(role, content, timestamp, intentStr) {
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




    function showTypingIndicator() {
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

    function showWelcome() {
        chatMessages.innerHTML = "";
        if (welcomeScreen) {
            const clone = welcomeScreen.cloneNode(true);
            clone.style.display = "flex";
            chatMessages.appendChild(clone);
            // Re-bind suggestion chips
            clone.querySelectorAll(".chip").forEach((chip) => {
                chip.addEventListener("click", () => sendSuggestion(chip));
            });
        }
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function autoResizeInput() {
        chatInput.style.height = "auto";
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
    }

    function closeMobileSidebar() {
        if (chatSidebar) chatSidebar.classList.remove("open");
    }

    // ── Event listeners ────────────────────────────────────────────
    btnNewChat.addEventListener("click", createNewChat);

    btnSend.addEventListener("click", () => sendMessage(chatInput.value));

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage(chatInput.value);
        }
    });

    chatInput.addEventListener("input", autoResizeInput);

    if (chatSidebarToggle) {
        chatSidebarToggle.addEventListener("click", () => {
            chatSidebar.classList.toggle("open");
        });
    }

    // ── Global: suggestion chip handler ────────────────────────────
    window.sendSuggestion = function (chipEl) {
        const text = chipEl.textContent.trim();
        chatInput.value = text;
        sendMessage(text);
    };

    // ── Init ───────────────────────────────────────────────────────
    (async function init() {
        await loadConversations();

        // If URL has a conversation UUID, auto-select it
        const urlConvId = getConversationIdFromUrl();
        if (urlConvId) {
            await selectConversation(urlConvId, false);
        }
    })();
})();
