// api.js is a module that will be used by the chatbot.js file to make API calls to the backend.
// It contains a function called api that will be used to make API calls to the backend.
// It is a module so it can be imported by the chatbot.js file.
// ── API helpers ────────────────────────────────────────────────
export async function api(url, options = {}) {
    try {
        const resp = await fetch(url, options);
        return await resp.json();
    } catch (err) {
        console.error("API error:", err);
        return null;
    }
}