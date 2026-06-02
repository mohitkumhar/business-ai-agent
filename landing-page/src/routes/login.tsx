import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { createMetaTags } from "@/lib/createMetaTags";
import { useState } from "react";
import { onboardingUrl, dashboardUrl, agentApiBaseUrl } from "@/constants";
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


function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

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
    try {
      const endpoint = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const payload = mode === "login" 
        ? { email, password } 
        : { email, password, name: fullName, business_name: businessName, phone };

      const res = await fetch(`${agentApiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        alert(data.message || "Authentication failed");
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
      alert("Failed to connect to backend");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex flex-col items-center justify-center relative overflow-hidden m-0 p-0">
      {/* Immersive background decoration */}
      <div className="absolute inset-0 bg-[#0a0a0a]" />
      <div className="absolute inset-0 bg-[url('$magicBackgrounds/magic-background.png')] bg-no-repeat bg-cover opacity-15 pointer-events-none" />
      <div className="absolute top-0 left-0 w-full h-full bg-linear-to-b from-blue-600/5 via-transparent to-[#FF5A25]/5 pointer-events-none" />

      <div className="relative z-10 w-full max-w-[480px] px-6 py-20 flex flex-col items-center">
        <div className="w-full p-10 md:p-14 rounded-[3.5rem] bg-black/60 border border-white/10 backdrop-blur-3xl shadow-[0_32px_100px_rgba(0,0,0,0.8)] relative overflow-hidden group">
          {/* Subtle brand accent */}
          <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#FF5A25]/10 rounded-full blur-[100px] pointer-events-none group-hover:bg-[#FF5A25]/15 transition-colors duration-1000" />

          <div className="relative z-10 w-full">
            <h1 className="text-4xl md:text-5xl font-bold text-center mb-4 text-white tracking-tighter">
              {mode === "login" ? "Access Pilot" : "Join Pilot"}
            </h1>
            <p className="text-center text-white/50 mb-12 font-medium text-lg tracking-tight">
              {mode === "login" ? "Navigate your business with AI." : "Let's set up your business mission."}
            </p>

            <button
              onClick={() => handleGoogleLogin()}
              disabled={isLoading}
              className="w-full mb-10 flex items-center justify-center gap-4 px-6 py-5 bg-white text-black rounded-[2rem] font-bold hover:bg-white/95 active:scale-[0.98] transition-all disabled:opacity-50 shadow-2xl shadow-white/5 text-lg"
            >
              <svg className="w-6 h-6" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Continue with Google
            </button>

            <div className="flex items-center gap-4 mb-10">
              <div className="h-px flex-1 bg-white/10" />
              <span className="text-white/20 text-[10px] font-black uppercase tracking-[0.4em] px-2">ENTRY</span>
              <div className="h-px flex-1 bg-white/10" />
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
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
                <div className="flex justify-between items-center px-1">
                  <label className="text-[11px] font-bold uppercase tracking-widest text-white/40 ml-1">Password</label>
                  {mode === "login" && <button type="button" className="text-[11px] font-bold text-blue-400 hover:text-blue-300 transition-colors">FORGOT?</button>}
                </div>
                <input
                  required
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-6 py-4 bg-white/[0.04] border border-white/10 rounded-2xl focus:outline-none focus:ring-2 focus:ring-[#FF5A25]/50 text-white placeholder-white/20 transition-all focus:bg-white/[0.08]"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="group relative overflow-hidden w-full py-5 text-white font-black rounded-[2rem] transition-all disabled:opacity-50 disabled:active:scale-100 mt-10 text-xl tracking-tight bg-linear-to-b border border-[#C4461D] from-[#FF8963] to-[#FF5A25] to-57% shadow-[inset_0_3px_2px_0_rgba(255,255,255,0.25),0_15px_40px_rgba(255,90,37,0.3)] active:from-[#E44A19] active:to-[#EF744C] active:from-43% active:to-100% active:shadow-[inset_0_-2px_2px_0_rgba(255,255,255,0.17)]"
              >
                {/* Visual brilliance shine */}
                <div className="bg-transparent group-hover:bg-white/40 w-1/4 absolute -left-[40%] group-hover:left-[120%] transition-[left] duration-0 group-hover:duration-700 blur-md -rotate-45 aspect-1/2 pointer-events-none" />

                {isLoading ? (
                  <div className="flex items-center gap-3 justify-center">
                    <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                    CONNECTING...
                  </div>
                ) : (
                  mode === "login" ? "ACCESS PILOT" : "CREATE ACCOUNT"
                )}
              </button>
            </form>

            <p className="mt-12 text-center text-white/30 text-xs font-bold uppercase tracking-[0.1em]">
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
      </div>
    </main>
  );
}
