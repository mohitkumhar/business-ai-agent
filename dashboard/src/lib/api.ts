"use client";

import { AGENT_API_BASE } from "./publicUrls";
import type { DashboardPeriod } from "./dashboardPeriod";
import { getPeriodBounds, periodLabel } from "./dashboardPeriod";
import { mockSummaryForPeriod, filterTransactionsByPeriod } from "./mockPeriod";

/**
 * Common Types for ProfitPilot API
 */
export interface DashboardSummary {
  total_revenue: number;
  total_expenses: number;
  net_profit: number;
  total_transactions: number;
  active_alerts: number;
  alert_highest_severity?: string | null;
  // Growth percentages
  revenue_change: number;
  expenses_change: number;
  net_profit_change: number;
  transactions_change: number;
}

export interface Transaction {
  transaction_id: number;
  transaction_date: string;
  type: string;
  category: string;
  amount: number;
  description: string;
}

export interface Alert {
  alert_id: number;
  created_at: string;
  alert_type: string;
  severity: string;
  message: string;
  status: string;
}

export type ForecastTrend = "up" | "down" | "stable" | "flat";

export interface Forecast {
  historical: { date: string; actual: number }[];
  forecast: { date: string; predicted: number; lower_bound: number; upper_bound: number }[];
  trend_direction: ForecastTrend;
  trend_percent: number;
  insight: string;
}

export interface BusinessInfo {
  business_id: string;
  business_name: string;
  industry_type: string;
  owner_name: string;
  city?: string;
  business_age?: string;
  employees_range?: string;
  monthly_revenue?: string;
  biggest_challenge?: string;
  finance_tracking_method?: string;
  user_name?: string;
  user_email?: string;
  onboarding_notes?: string;
}


// Interfaces for Charts (Kushal-dev)
export interface RevenueVsExpense { labels: string[]; revenue: number[]; expenses: number[]; }
export interface SalesTrend { labels: string[]; revenue: number[]; expenses: number[]; }
export interface FinancialOverview { labels: string[]; revenue: number[]; expenses: number[]; net_profit: number[]; cash_balance: number[]; }
export interface AlertsBySeverity { labels: string[]; data: number[]; }
export interface TopProducts { labels: string[]; stock: number[]; margin: number[]; margin_amount?: number[]; margin_pct?: number[]; }
export interface EmployeeStats { labels: string[]; counts: number[]; avg_salary: number[]; }
export interface SalesTarget { business_name: string; current_revenue: number; target_revenue: number; percentage: number; }
export interface Alert { alert_id: number; created_at: string; alert_type: string; severity: string; message: string; status: string; }
export interface HealthScore { name: string; overall: number; cash: number; profitability: number; growth: number; cost_control: number; risk: number; }
export interface HealthScores { businesses: string[]; scores: HealthScore[]; }




// --- Helpers ---
function withPeriod(baseUrl: string, period: DashboardPeriod): string {
  const sep = baseUrl.includes("?") ? "&" : "?";
  return `${baseUrl}${sep}period=${period}`;
}

async function fetchWithFallback<T>(url: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) return fallback;
    return res.json();
  } catch {
    return fallback;
  }
}

function escapeCsvCell(cell: string): string {
  if (cell.includes(",") || cell.includes("\"") || cell.includes("\n")) {
    return `"${cell.replace(/"/g, "\"\"")}"`;
  }
  return cell;
}

// --- API Wrapper Object ---
function getHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("profit_pilot_token") : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { "Authorization": `Bearer ${token}` } : {}),
  } as HeadersInit;
}

export const api = {
  getSummary: async (period: string): Promise<DashboardSummary> => {
    const res = await fetch(`/api/dashboard/summary-sql?period=${period}`, { headers: getHeaders() });
    if (!res.ok) throw new Error("Summary API failed");
    return res.json();
  },

  getFinancialOverview: async (period?: string): Promise<FinancialOverview> => {
    const res = await fetch(`/api/dashboard/financial-overview${period ? `?period=${period}` : ""}`, { headers: getHeaders() });
    return res.json();
  },

  getSalesTarget: async (period: string): Promise<SalesTarget> => {
    const res = await fetch(`/api/dashboard/sales-target?period=${period}`, { headers: getHeaders() });
    return res.json();
  },


  getRevenueVsExpense: async (period: string) => {
    const res = await fetch(`/api/dashboard/revenue-vs-expense?period=${period}`, { headers: getHeaders() });
    return res.json();
  },

  getSalesTrend: async (period: string) => {
    const res = await fetch(`/api/dashboard/sales-trend?period=${period}`, { headers: getHeaders() });
    return res.json();
  },

  getForecast: async (period: string): Promise<Forecast> => {
    const res = await fetch(`/api/dashboard/forecast?period=${period}`, { headers: getHeaders() });
    if (!res.ok) {
      const { mockForecast } = await import("./mockData");
      return mockForecast;
    }
    return res.json();
  },

  getRecentTransactions: async (params: { search?: string; category?: string; limit?: number; period?: string; }) => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.category) query.set("category", params.category);
    if (params.limit) query.set("limit", params.limit.toString());
    if (params.period) query.set("period", params.period);
    const res = await fetch(`/api/dashboard/recent-transactions?${query.toString()}`, { headers: getHeaders() });
    return res.json();
  },

  getAlertsList: async (period?: string) => {
    const res = await fetch(`/api/dashboard/alerts-list${period ? `?period=${period}` : ""}`, { headers: getHeaders() });
    return res.json();
  },


  getBusinessInfo: async (): Promise<BusinessInfo> => {
    const res = await fetch(`/api/dashboard/business-info`, { headers: getHeaders() });
    return res.json();
  },

  // Other endpoints
  getCategories: async () => (await fetch(`/api/dashboard/categories`, { headers: getHeaders() })).json(),
  getAlertsBySeverity: async (period?: string) => (await fetch(`/api/dashboard/alerts-by-severity${period ? `?period=${period}` : ""}`, { headers: getHeaders() })).json(),
  getHealthScores: async (period?: string) => (await fetch(`/api/dashboard/health-scores${period ? `?period=${period}` : ""}`, { headers: getHeaders() })).json(),
  getTopProducts: async (period?: string) => (await fetch(`/api/dashboard/top-products${period ? `?period=${period}` : ""}`, { headers: getHeaders() })).json(),
  getEmployeeStats: async (period?: string) => (await fetch(`/api/dashboard/employee-stats${period ? `?period=${period}` : ""}`, { headers: getHeaders() })).json(),


  /** Export data as CSV (Restored) */
  exportDashboardCsv: async (period: string) => {
    const params = new URLSearchParams({ period });
    const res = await fetch(`/api/dashboard/export-csv?${params.toString()}`, { headers: getHeaders() });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `profitpilot_export_${period}_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },
};


/**
 * Chat Streaming Logic (Testsparkhack)
 */
export async function* streamChatSend(conversationId: string, message: string) {
  const res = await fetch(`${AGENT_API_BASE}/api/chat/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
  if (!res.ok) throw new Error("Chat sequence failed");
  const reader = res.body?.getReader();
  if (!reader) return;
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (value) buffer += decoder.decode(value, { stream: true });
    while (buffer.includes("\n\n")) {
      const i = buffer.indexOf("\n\n");
      const raw = buffer.slice(0, i).trim();
      buffer = buffer.slice(i + 2);
      if (raw.startsWith("data: ")) yield JSON.parse(raw.slice(6));
    }
    if (done) break;
  }
}
