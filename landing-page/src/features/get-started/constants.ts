export const inputClasses =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-white/40 transition-shadow";

export const selectClasses =
  "w-full px-4 py-3 bg-[#111] border border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-white transition-shadow appearance-none cursor-pointer";

export const CHALLENGES = [
  "Cash Flow",
  "Low Sales",
  "High Expenses",
  "Marketing",
  "Hiring/Staff",
  "Pricing",
  "Growth Planning",
] as const;

export const FINANCE_TRACKING_METHODS = [
  "Excel/Sheets",
  "App like Tally/Zoho",
  "Notebook/Manual",
  "Don't track",
] as const;