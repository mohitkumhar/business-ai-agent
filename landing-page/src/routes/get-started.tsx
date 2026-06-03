import { createFileRoute } from "@tanstack/react-router";
import { Button } from "@typebot.io/ui/components/Button";
import { createMetaTags } from "@/lib/createMetaTags";
import { agentApiBaseUrl, dashboardUrl, signinUrl } from "@/constants";
import { markUserOnboarded, normalizeEmail } from "@/lib/onboardingState";
import { useEffect, useState } from "react";
import { motion } from "motion/react";

export const Route = createFileRoute("/get-started")({
  head: () => ({
    meta: createMetaTags({
      title: "Get Started | ProfitPilot",
      description:
        "Get started with ProfitPilot by telling us about your business.",
      imagePath: "/images/default-og.png",
      path: "/get-started",
    }),
  }),
  component: GetStartedPage,
});

const inputClasses =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-white/40 transition-shadow";
const selectClasses =
  "w-full px-4 py-3 bg-[#111] border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-shadow appearance-none cursor-pointer";

function GetStartedPage() {
  const [sessionReady, setSessionReady] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    full_name: "",
    phone: "",
    email: "",
    business_name: "",
    business_category: "",
    city: "",
    employees_range: "",
    monthly_revenue: "",
    business_age: "",
    challenges: [] as string[],
    finance_tracking_method: "",
    onboarding_notes: "",
  });

  useEffect(() => {
    const savedUser = localStorage.getItem("profit_pilot_user");
    if (!savedUser) {
      window.location.replace(signinUrl);
      return;
    }
    try {
      const user = JSON.parse(savedUser) as {
        full_name?: string;
        email?: string;
        phone?: string;
      };
      setFormData((prev) => ({
        ...prev,
        full_name: user.full_name || prev.full_name,
        email: user.email || prev.email,
        phone: user.phone || prev.phone,
      }));
    } catch (e) {
      console.error("Failed to parse saved user data", e);
    }
    setSessionReady(true);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleChallengeChange = (challenge: string) => {
    setFormData(prev => {
      const current = [...prev.challenges];
      if (current.includes(challenge)) {
        return { ...prev, challenges: current.filter(c => c !== challenge) };
      } else {
        return { ...prev, challenges: [...current, challenge] };
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    if (formData.challenges.length === 0) {
      setError("Please select at least one challenge under Step 3.");
      setIsSubmitting(false);
      return;
    }

    const emailNorm = normalizeEmail(formData.email);
    if (!emailNorm) {
      setError("A valid work email is required.");
      setIsSubmitting(false);
      return;
    }

    try {
      const apiBase = agentApiBaseUrl;
      const response = await fetch(`${apiBase}/api/v1/onboarding`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          email: emailNorm,
          biggest_challenge: formData.challenges.join(", "),
        }),
      });

      const result = (await response.json()) as {
        error?: string;
        message?: string;
        is_error?: boolean;
      };
      if (response.ok) {
        markUserOnboarded(emailNorm);
        const userStr = localStorage.getItem("profit_pilot_user") || "{}";
        const user = JSON.parse(userStr) as Record<string, unknown>;
        localStorage.setItem(
          "profit_pilot_user",
          JSON.stringify({
            ...user,
            full_name: formData.full_name,
            email: formData.email.trim(),
          }),
        );
        setIsSubmitted(true);
      } else {
        setError(
          result.error ||
            result.message ||
            "Failed to submit form. Please try again.",
        );
      }
    } catch (err) {
      setError(
        `Connection error. Is the backend running at ${agentApiBaseUrl}?`,
      );
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!sessionReady) {
    return (
      <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex items-center justify-center m-0">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          <p className="text-white/50 text-sm">Loading…</p>
        </div>
      </main>
    );
  }

  if (isSubmitted) {
    return (
      <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex flex-col pt-32 pb-24 px-4 m-0 overflow-x-hidden">
        <div className="max-w-2xl w-full mx-auto flex flex-col items-center gap-6 py-32 text-center animate-in fade-in duration-500">
            <h1 className="text-4xl md:text-5xl font-bold">
              Form Submitted Successfully!
            </h1>
            <p className="text-lg text-white/70">
              Welcome to ProfitPilot! We've received your business details and are setting up your workspace.
            </p>
            <Button
              onClick={() => window.location.href = `${dashboardUrl}?user_email=${encodeURIComponent(formData.email)}`}
              variant="outline"
              style={{ color: "black", backgroundColor: "white", borderColor: "white" }}
              className="mt-6 rounded-full font-medium"
            >
              Go to Dashboard
            </Button>
          </div>
      </main>
    );
  }

  return (
    <main className="dark w-full min-h-screen bg-[#0a0a0a] text-white flex flex-col pt-24 md:pt-32 pb-32 px-4 m-0 overflow-x-hidden">
        <div className="max-w-3xl w-full mx-auto pb-24 mt-8 md:mt-16 animate-in slide-in-from-bottom-8 fade-in duration-700">
          <div className="mb-12 text-center flex flex-col gap-4 mx-auto w-full max-w-2xl">
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
              Business Profile
            </h1>
            <p className="text-lg text-white/60 mx-auto">
              Tell us about your company so we can tailor your dynamic AI dashboard.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-8 md:gap-12">
            {/* Step 1 */}
            <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-6">
              <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
                Step 1 — Your Details
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    Your Full Name <span className="text-red-400">*</span>
                  </label>
                  <input
                    required
                    type="text"
                    name="full_name"
                    className={inputClasses}
                    placeholder="Jane Doe"
                    value={formData.full_name}
                    onChange={handleChange}
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    Work Email <span className="text-red-400">*</span>
                  </label>
                  <input
                    required
                    type="email"
                    name="email"
                    className={inputClasses}
                    placeholder="name@company.com"
                    value={formData.email}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-6">
              <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
                Step 2 — Business Details
              </h2>
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-white/80">
                  Company / Business Name <span className="text-red-400">*</span>
                </label>
                <input
                  required
                  type="text"
                  name="business_name"
                  className={inputClasses}
                  placeholder="Your Business Name"
                  value={formData.business_name}
                  onChange={handleChange}
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    Business Category
                  </label>
                  <select 
                    name="business_category"
                    className={selectClasses} 
                    value={formData.business_category}
                    onChange={handleChange}
                  >
                    <option value="" disabled>Select a category</option>
                    <option>Retail/Shop</option>
                    <option>Restaurant/Food</option>
                    <option>Manufacturing</option>
                    <option>Wholesale/Distribution</option>
                    <option>Services</option>
                    <option>E-commerce/Online</option>
                    <option>Education/Coaching</option>
                    <option>Real Estate</option>
                    <option>Logistics/Transport</option>
                    <option>Freelance/Consulting</option>
                    <option>Other</option>
                  </select>
                </div>
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    City / Location <span className="text-red-400">*</span>
                  </label>
                  <input
                    required
                    type="text"
                    name="city"
                    className={inputClasses}
                    placeholder="City, Country"
                    value={formData.city}
                    onChange={handleChange}
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    Number of Employees
                  </label>
                  <select
                    name="employees_range"
                    className={selectClasses}
                    value={formData.employees_range}
                    onChange={handleChange}
                  >
                    <option value="" disabled>Select employees</option>
                    <option>Just me</option>
                    <option>2–5</option>
                    <option>6–15</option>
                    <option>16–50</option>
                    <option>51–100</option>
                    <option>100+</option>
                  </select>
                </div>
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium text-white/80">
                    Monthly Revenue
                  </label>
                  <select 
                    name="monthly_revenue"
                    className={selectClasses}
                    value={formData.monthly_revenue}
                    onChange={handleChange}
                  >
                    <option value="" disabled>Select monthly revenue</option>
                    <option>Under ₹50K</option>
                    <option>₹50K–₹2L</option>
                    <option>₹2L–₹10L</option>
                    <option>₹10L–₹50L</option>
                    <option>Above ₹50L</option>
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-white/80">
                  Business Age
                </label>
                <select 
                  name="business_age"
                  className={selectClasses}
                  value={formData.business_age}
                  onChange={handleChange}
                >
                  <option value="" disabled>Select business age</option>
                  <option>0–6 months</option>
                  <option>Less than 1 year</option>
                  <option>1–3 years</option>
                  <option>3–7 years</option>
                  <option>7+ years</option>
                </select>
              </div>
            </div>

            {/* Step 3 */}
            <div className="p-6 md:p-10 md:rounded-3xl rounded-2xl border border-white/10 bg-white/[0.02] shadow-xl flex flex-col gap-8">
              <h2 className="text-2xl font-medium text-white/90 border-b border-white/5 pb-4">
                Step 3 — Your Current Situation
              </h2>

              <div className="flex flex-col gap-5">
                <label className="text-sm font-medium text-white/80">
                  Biggest Challenges <span className="text-red-400">*</span>
                </label>
                <div className="flex flex-wrap gap-3">
                  {[
                    "Cash Flow",
                    "Low Sales",
                    "High Expenses",
                    "Marketing",
                    "Hiring/Staff",
                    "Pricing",
                    "Growth Planning",
                  ].map((challenge) => (
                    <label
                      key={challenge}
                      className={`cursor-pointer border rounded-full px-5 py-2.5 text-sm transition-all relative ${
                        formData.challenges.includes(challenge)
                          ? "bg-white border-white text-black font-medium"
                          : "border-white/20 bg-white/5 hover:bg-white/10 text-white"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={formData.challenges.includes(challenge)}
                        onChange={() => handleChallengeChange(challenge)}
                        className="absolute opacity-0 w-0 h-0"
                      />
                      {challenge}
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-5">
                <label className="text-sm font-medium text-white/80">
                  Finance Tracking Method
                </label>
                <div className="flex flex-wrap gap-3">
                  {[
                    "Excel/Sheets",
                    "App like Tally/Zoho",
                    "Notebook/Manual",
                    "Don't track",
                  ].map((method) => (
                    <label
                      key={method}
                      className={`cursor-pointer border rounded-full px-5 py-2.5 text-sm transition-all relative ${
                        formData.finance_tracking_method === method
                          ? "bg-white border-white text-black font-medium"
                          : "border-white/20 bg-white/5 hover:bg-white/10 text-white"
                      }`}
                    >
                      <input
                        type="radio"
                        name="finance_tracking_method"
                        value={method}
                        checked={formData.finance_tracking_method === method}
                        onChange={handleChange}
                        className="absolute opacity-0 w-0 h-0"
                      />
                      {method}
                    </label>
                  ))}
                </div>

                {/* Conditional Sub-options for Digital Methods */}
                {(formData.finance_tracking_method === "Excel/Sheets" || 
                  formData.finance_tracking_method === "App like Tally/Zoho") && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }} 
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-6 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-4 animate-in fade-in"
                  >
                    <p className="text-sm text-white/70 italic">
                      Almost ready! Would you like to upload your initial data now for instant analysis?
                    </p>
                    <div className="flex gap-4">
                      <div className="flex-1 border-2 border-dashed border-white/10 rounded-xl p-8 hover:border-[#FF5A25]/50 transition-colors flex flex-col items-center justify-center gap-3 cursor-pointer group">
                        <svg className="w-8 h-8 text-white/30 group-hover:text-[#FF5A25] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                        </svg>
                        <span className="text-sm font-medium">Upload File (.xlsx, .csv)</span>
                        <input type="file" className="hidden" accept=".xlsx,.csv" />
                      </div>
                      <button 
                        type="button"
                        className="px-6 py-2 text-sm font-medium text-white/40 hover:text-white transition-colors"
                      >
                        Skip for now
                      </button>
                    </div>
                  </motion.div>
                )}

                {/* Conditional Upload for Manual Notebook */}
                {formData.finance_tracking_method === "Notebook/Manual" && (
                  <motion.div 
                    initial={{ opacity: 0, y: -10 }} 
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 p-6 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-4 animate-in fade-in"
                  >
                    <p className="text-sm text-white/70 italic">
                      No problem! Take a photo of your latest ledger entries and our AI will extract the data for you.
                    </p>
                    <div className="border-2 border-dashed border-white/10 rounded-xl p-8 hover:border-[#FF5A25]/50 transition-colors flex flex-col items-center justify-center gap-3 cursor-pointer group">
                      <svg className="w-8 h-8 text-white/30 group-hover:text-[#FF5A25] transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      <span className="text-sm font-medium">Upload Image of Notebook</span>
                      <input type="file" className="hidden" accept="image/*" capture="environment" />
                    </div>
                  </motion.div>
                )}
              </div>

              <div className="flex flex-col gap-3">
                <label className="text-sm font-medium text-white/80">
                  Anything else AI should know (optional)
                </label>
                <textarea
                  name="onboarding_notes"
                  className={`${inputClasses} min-h-[120px] resize-y leading-relaxed`}
                  placeholder="Tell us more about your specific needs or pain points..."
                  value={formData.onboarding_notes}
                  onChange={handleChange}
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-4 rounded-2xl text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-end pt-4">
              <Button
                disabled={isSubmitting}
                type="submit"
                size="lg"
                className="group relative overflow-hidden w-full md:w-auto px-12 py-8 text-xl font-bold rounded-full transition-all disabled:opacity-50 disabled:active:scale-100 shadow-[inset_0_3px_2px_0_rgba(255,255,255,0.25),0_10px_40px_rgba(255,90,37,0.2)] bg-linear-to-b border border-[#C4461D] from-[#FF8963] to-[#FF5A25] text-white active:shadow-[inset_0_-2px_2px_0_rgba(255,255,255,0.17)] flex items-center justify-center gap-3"
              >
                {/* Shine effect */}
                <div className="bg-transparent group-hover:bg-white/40 w-1/4 absolute -left-[40%] group-hover:left-[120%] transition-[left] duration-0 group-hover:duration-700 blur-md -rotate-45 aspect-square pointer-events-none" />
                
                {isSubmitting ? (
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                    Connecting...
                  </div>
                ) : (
                  "Launch My Dashboard"
                )}
              </Button>
            </div>
          </form>
        </div>
    </main>
  );
}
