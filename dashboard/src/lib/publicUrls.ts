/** Landing (Vite / TanStack) — runs on port 3003 in dev, port 5173 in Docker. */

const DEFAULT_LANDING_PAGE = "http://localhost:3003";
function resolveLandingPageUrl(): string {
  const raw = (process.env.NEXT_PUBLIC_LANDING_URL ?? "").trim();
  if (!raw) return DEFAULT_LANDING_PAGE;
  // Common mistake: port 3000 is Grafana in this repo's docker-compose, not the marketing site.
  if (raw === "http://localhost:3000" || raw === "http://127.0.0.1:3000") {
    return DEFAULT_LANDING_PAGE;
  }
  return raw.replace(/\/$/, "");
}

export const LANDING_PAGE_URL = resolveLandingPageUrl();

/**
 * Flask API base. Default "" = same-origin; `next.config.ts` rewrites `/api/*` to Flask
 * (works with Docker `AGENT_API_URL=http://backend:5000` on the server).
 * Set `NEXT_PUBLIC_AGENT_API_URL` only to force a direct URL (e.g. cross-origin debugging).
 */
export const AGENT_API_BASE = (
  process.env.NEXT_PUBLIC_AGENT_API_URL ?? ""
).replace(/\/$/, "");
