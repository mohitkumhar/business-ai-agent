export const breakpoints = {
  md: 768,
};

export const currentBaseUrl = "/";
export const signinUrl = "/login";
export const registerUrl = `/login`;
export const onboardingUrl = `/get-started`;

/** Browser: backend Flask (onboarding + agent APIs). Override with VITE_AGENT_API_URL in .env */
export const agentApiBaseUrl =
  typeof import.meta !== "undefined" && import.meta.env?.VITE_AGENT_API_URL
    ? String(import.meta.env.VITE_AGENT_API_URL).replace(/\/$/, "")
    : "http://localhost:5000";

/** Dashboard Next app URL; query ?user_email= is appended after onboarding. */
export const dashboardUrl =
  typeof import.meta !== "undefined" && import.meta.env?.VITE_DASHBOARD_URL
    ? String(import.meta.env.VITE_DASHBOARD_URL).replace(/\/$/, "")
    : "http://localhost:3001";
export const githubRepoUrl = "https://github.com/mohitkumhar/intelligent-business-agent";
export const linkedInUrl = "https://www.linkedin.com/in/mohitkumhar";
export const discordUrl = "https://github.com/mohitkumhar/intelligent-business-agent";
export const docsUrl = "https://github.com/mohitkumhar/intelligent-business-agent#readme";
export const howToGetHelpUrl = "https://github.com/mohitkumhar/intelligent-business-agent/issues";
export const stripeClimateUrl = "/";
export const enterpriseLeadProfitPilotUrl =
  "https://github.com/mohitkumhar/intelligent-business-agent";

export const legacyRedirects = {
  "/profitpilot-lib": "/",
  "/profitpilot-lib/v2": "/",
} as const;