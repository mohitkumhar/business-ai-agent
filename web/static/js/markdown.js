// unsafe markdown selectors and url attributes constants
const UNSAFE_MARKDOWN_SELECTORS = [
    "script", "style", "iframe", "object", "embed", "link", "meta",
    "base", "form", "input", "button", "textarea", "select",
].join(",");
const URL_ATTRIBUTES = new Set(["href", "src", "action", "formaction", "poster", "xlink:href"]);


// url sanitization helpers
export function isSafeMarkdownUrl(value) {
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
// markdown sanitization helper
export function sanitizeMarkdownFragment(fragment) {
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
// markdown rendering helper
export function renderSafeMarkdown(container, markdownText) {
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