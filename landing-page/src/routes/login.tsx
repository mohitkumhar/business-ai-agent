import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ContentPageWrapper } from "@/components/ContentPageWrapper";
import { createMetaTags } from "@/lib/createMetaTags";
import { useState } from "react";
import { onboardingUrl, dashboardUrl } from "@/constants";
import { isUserOnboarded, normalizeEmail } from "@/lib/onboardingState";
import { useGoogleLogin } from "@react-oauth/google";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: createMetaTags({
      title: "Login | ProfitPilot",
      description: "Log in to your ProfitPilot account to access your AI business partner.",
      imagePath: "/images/default-og.png",
      path: "/login",
    }),
  }),
  component: LoginPage,
});

const agentApiBaseUrl = "http://localhost:5000";

function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Implement actual Google Login
  const handleGoogleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      setIsLoading(true);
      try {
        // Fetch user info from Google's userinfo endpoint
        const res = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
        });
        const user = await res.json();
        // Extract basic data
        // Extract basic data
        if (user.email) {
          const registry: string[] = JSON.parse(localStorage.getItem("profit_pilot_registry") || "[]");
          const emailNorm = normalizeEmail(user.email);
          const userExists = registry.some((e) => normalizeEmail(e) === emailNorm);
          const onboarded = isUserOnboarded(user.email);
          localStorage.setItem(
            "profit_pilot_user",
            JSON.stringify({
              full_name: user.name || user.given_name || "",
              email: user.email,
              phone: "",
            }),
          );
          if (onboarded) {
            window.location.href = `${dashboardUrl}?user_email=${encodeURIComponent(user.email)}`;
            return;
          }
          if (!userExists) {
            const updatedRegistry = [...new Set([...registry, emailNorm])];
            localStorage.setItem("profit_pilot_registry", JSON.stringify(updatedRegistry));
          }
          navigate({ to: onboardingUrl });
        }
      } catch (err) {
        console.error("Failed to fetch Google user info:", err);
      } finally {
        setIsLoading(false);
      }
    },
    onError: (error) => {
      console.error("Google Login Failed:", error);
      setIsLoading(false);
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const payload =
        mode === "login"
          ? { email, password }
          : { email, password, name: fullName, business_name: businessName, phone };
      const res = await fetch(`${agentApiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMessage(data.message || "Authentication failed");
        return;
      }
      // Store token and user info
      localStorage.setItem("profit_pilot_token", data.token);
      localStorage.setItem("profit_pilot_user", JSON.stringify(data.user || { email }));
      // Determine next step
      const onboarded = isUserOnboarded(email);
      if (onboarded) {
        window.location.href = `${dashboardUrl}?user_email=${encodeURIComponent(email)}`;
      } else {
        navigate({ to: onboardingUrl });
      }
    } catch (err) {
      console.error("Auth error:", err);
      setErrorMessage("Failed to connect to backend");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ContentPageWrapper>
      <div className="min-h-screen flex items-center justify-center bg-[#0A0A0A] px-4 py-16 relative overflow-hidden">
        {/* Immersive background decoration */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#FF5A25]/5 via-transparent to-[#FF8963]/3 pointer-events-none" />
        {/* Subtle brand accent */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[1px] bg-gradient-to-r from-transparent via-[#FF5A25]/30 to-transparent" />

        <div className="w-full max-w-md">
          <div className="mb-12 text-center">
            <h1 className="text-4xl font-black text-white mb-3 tracking-tight">
              {mode === "login" ? "Access Pilot" : "Join Pilot"}
            </h1>
            <p className="text-white/40 text-base">
              {mode === "login" ? "Navigate your business with AI." : "Let's set up your business mission."}
            </p>
          </div>

          <button
            onClick={() => handleGoogleLogin()}
            disabled={isLoading}
            className="w-full mb-10 flex items-center justify-center gap-4 px-6 py-5 bg-white text-black rounded-[2rem] font-bold hover:bg-white/95 active:scale-[0.98] transition-all disabled:opacity-50 shadow-2xl shadow-white/5 text-lg"
          >
            Continue with Google
          </button>

          <div className="flex items-center gap-4 mb-10">
            <div className="flex-1 h-px bg-white/8" />
            <span className="text-white/20 text-xs font-bold tracking-widest uppercase"> ENTRY </span>
            <div className="flex-1 h-px bg-white/8" />
          </div>

          {errorMessage && (
            <div
              role="alert"
              aria-live="assertive"
              className="mb-6 px-4 py-3 rounded-2xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm"
            >
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {mode === "signup" && (
              <>
                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-widest text-white/40 ml-2">Full Name</label>
                  <input
                    required
                    type="text"
                    placeholder="Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-widest text-white/40 ml-2">Business Name</label>
                  <input
                    required
                    type="text"
                    placeholder="Acme Corp"
                    value={businessName}
                    onChange={(e) => setBusinessName(e.target.value)}
                    className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[11px] font-bold uppercase tracking-widest text-white/40 ml-2">Phone / WhatsApp</label>
                  <input
                    required
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
                  />
                </div>
              </>
            )}

            <div className="space-y-2">
              <label className="text-[11px] font-bold uppercase tracking-widest text-white/40 ml-2">Work Email</label>
              <input
                required
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between ml-2">
                <label className="text-[11px] font-bold uppercase tracking-widest text-white/40">Password</label>
                {mode === "login" && (
                  <button
                    type="button"
                    className="text-[10px] font-bold uppercase tracking-widest text-white/20 hover:text-white/50 transition-colors"
                  >
                    FORGOT?
                  </button>
                )}
              </div>
              <input
                required
                type="password"
                placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="relative w-full mt-8 px-6 py-5 bg-[#FF5A25] text-white rounded-[2rem] font-black text-base tracking-widest uppercase hover:bg-[#FF6B35] active:scale-[0.98] transition-all disabled:opacity-50 overflow-hidden shadow-2xl shadow-[#FF5A25]/20"
            >
              {/* Visual brilliance shine */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full" />
              {isLoading ? (
                <span className="flex items-center justify-center gap-2">
                  CONNECTING...
                </span>
              ) : (
                mode === "login" ? "ACCESS PILOT" : "CREATE ACCOUNT"
              )}
            </button>
          </form>

          <p className="text-center mt-10 text-white/30 text-sm">
            {mode === "login" ? "New to ProfitPilot?" : "Account holder?"}{" "}
            <button
              type="button"
              onClick={() => setMode(mode === "login" ? "signup" : "login")}
              className="text-white hover:text-[#FF8963] transition-colors underline underline-offset-8 decoration-white/10 hover:decoration-[#FF8963]/50"
            >
              {mode === "login" ? "START MISSION" : "LOGIN"}
            </button>
          </p>
        </div>
      </div>
    </ContentPageWrapper>
  );
}
