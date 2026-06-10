"use client";

import { AGENT_API_BASE } from "./publicUrls";
import type { ChatConversation, ChatMessage } from "./chatHistory";

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

export type ForecastTrend = "up" | "down" | "flat";

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
export interface HealthScore { name: string; overall: number; cash: number; profitability: number; growth: number; cost_control: number; risk: number; }
export interface HealthScores { businesses: string[]; scores: HealthScore[]; }
export interface Categories {categories: string[];}



// --- API Wrapper Object ---
// --- API Wrapper Object ---
function getHeaders() {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("profit_pilot_token")
      : null;

  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  } as HeadersInit;
}
async function safeFetchJson<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, options);

  if (!res.ok) {
    const contentType = res.headers.get("content-type") || "";
    let message = `HTTP ${res.status}`;

    try {
      if (contentType.includes("application/json")) {
        const data = await res.json();
        message = data?.message || JSON.stringify(data);
      } else {
        message = await res.text();
      }
    } catch {
      // Ignore parsing failures
    }

    throw new Error(message);
  }

  return res.json();
}

export function getAuthHeaders() {
  const token = typeof window !== "undefined" ? localStorage.getItem("profit_pilot_token") : null;
  return token ? ({ Authorization: `Bearer ${token}` } as HeadersInit) : ({} as HeadersInit);
}

async function readJsonOrThrow<T>(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(input, init);

  if (!response.ok) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  return response.json();
}

function chatApiPath(path: string): string {
  return AGENT_API_BASE ? `${AGENT_API_BASE}${path}` : path;
}

export const api = {
  getSummary: async (
  period: string
): Promise<DashboardSummary> => {
  const res = await fetch(
    `/api/dashboard/summary-sql?period=${period}`,
    { headers: getHeaders() }
  );

 if (!res.ok) {
  const text = await res.text();
  throw new Error(
    `Summary API failed (${res.status}): ${text}`
  );
}
  return res.json();
},
  getFinancialOverview: async (
    period?: string
  ): Promise<FinancialOverview> => {
    return safeFetchJson<FinancialOverview>(
      `/api/dashboard/financial-overview${period ? `?period=${period}` : ""}`,
      { headers: getHeaders() }
    );
  },
  getRevenueVsExpense: async (
  period: string
): Promise<RevenueVsExpense> =>
  safeFetchJson<RevenueVsExpense>(
    `/api/dashboard/revenue-vs-expense?period=${period}`,
    { headers: getHeaders() }   
  ),

  getSalesTarget: async (
    period: string
  ): Promise<SalesTarget> => {
    return safeFetchJson<SalesTarget>(
      `/api/dashboard/sales-target?period=${period}`,
      { headers: getHeaders() }
    );
  },
 getSalesTrend: async (
  period: string
): Promise<SalesTrend> => {
  return safeFetchJson<SalesTrend>(
    `/api/dashboard/sales-trend?period=${period}`,
    { headers: getHeaders() }
  );
},

getForecast: async (period: string): Promise<Forecast> => {
  const res = await fetch(
    `/api/dashboard/forecast?period=${period}`,
    { headers: getHeaders() }
  );

  if (!res.ok) {
    const { mockForecast } = await import("./mockData");
    return mockForecast;
  }

  return res.json();
},

getRecentTransactions: async (params: {
  search?: string;
  category?: string;
  limit?: number;
  period?: string;
}) => {
  const query = new URLSearchParams();

  if (params.search) query.set("search", params.search);
  if (params.category) query.set("category", params.category);
  if (params.limit) query.set("limit", params.limit.toString());
  if (params.period) query.set("period", params.period);

  const res = await fetch(
  `/api/dashboard/recent-transactions?${query.toString()}`,
  { headers: getHeaders() }
);

if (!res.ok) {
  const text = await res.text();
  throw new Error(
    `Recent transactions API failed (${res.status}): ${text}`
  );
}

return res.json();
},

getAlertsList: async (period?: string) => {
  const res = await fetch(
    `/api/dashboard/alerts-list${period ? `?period=${period}` : ""}`,
    { headers: getHeaders() }
  );

  return res.json();
},

getBusinessInfo: async (): Promise<BusinessInfo> => {
  return safeFetchJson<BusinessInfo>(
    `/api/dashboard/business-info`,
    { headers: getHeaders() }
  );
},

// Other endpoints
getCategories: async (): Promise<Categories> =>
  safeFetchJson<Categories>(
    `/api/dashboard/categories`,
    { headers: getHeaders() }
  ),

getAlertsBySeverity: async (
  period?: string
): Promise<AlertsBySeverity> =>
  safeFetchJson<AlertsBySeverity>( `/api/dashboard/alerts-by-severity${period ? `?period=${period}` : ""}`,
    { headers: getHeaders() }
  ),


getHealthScores: async (
  period?: string
): Promise<HealthScores> =>
  safeFetchJson<HealthScores>( `/api/dashboard/health-scores${period ? `?period=${period}` : ""}`,
    { headers: getHeaders() }
  ),

getTopProducts: async (period?: string): Promise<TopProducts> =>
  safeFetchJson<TopProducts>(
    `/api/dashboard/top-products${period ? `?period=${period}` : ""}`,
    { headers: getHeaders() }
  ),

getEmployeeStats: async (
  period?: string
): Promise<EmployeeStats> =>
  safeFetchJson<EmployeeStats>(
    `/api/dashboard/employee-stats${period ? `?period=${period}` : ""}`,
    { headers: getHeaders() }
  ),




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


export async function listChatConversations(): Promise<ChatConversation[]> {
  const payload = await readJsonOrThrow<{ conversations: ChatConversation[] }>(
    chatApiPath("/api/chat/conversations"),
    {
      cache: "no-store",
      headers: getHeaders(),
    }
  );
  return payload.conversations ?? [];
}

export async function getChatConversation(conversationId: string): Promise<ChatConversation> {
  const payload = await readJsonOrThrow<{ conversation: ChatConversation }>(
    chatApiPath(`/api/chat/conversations/${encodeURIComponent(conversationId)}`),
    {
      cache: "no-store",
      headers: getHeaders(),
    }
  );
  return payload.conversation;
}

export async function upsertChatConversation(conversation: ChatConversation): Promise<ChatConversation> {
  const payload = await readJsonOrThrow<{ conversation: ChatConversation }>(
    chatApiPath(`/api/chat/conversations/${encodeURIComponent(conversation.id)}`),
    {
      method: "PUT",
      headers: getHeaders(),
      body: JSON.stringify({
        title: conversation.title,
        createdAt: conversation.createdAt,
        updatedAt: conversation.updatedAt,
        messages: conversation.messages,
      }),
    }
  );
  return payload.conversation;
}

export async function appendChatMessage(
  conversationId: string,
  title: string,
  message: ChatMessage,
  metadata?: { createdAt?: number; updatedAt?: number }
): Promise<ChatConversation> {
  const payload = await readJsonOrThrow<{ conversation: ChatConversation }>(
    chatApiPath(`/api/chat/conversations/${encodeURIComponent(conversationId)}/messages`),
    {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({
        title,
        createdAt: metadata?.createdAt,
        updatedAt: metadata?.updatedAt ?? message.timestamp,
        message,
      }),
    }
  );
  return payload.conversation;
}

export async function removeChatConversation(conversationId: string): Promise<void> {
  const response = await fetch(
    chatApiPath(`/api/chat/conversations/${encodeURIComponent(conversationId)}`),
    {
      method: "DELETE",
      headers: getHeaders(),
    }
  );
  if (!response.ok && response.status !== 404) {
    const errorText = await response.text().catch(() => response.statusText);
    throw new Error(errorText || `Delete failed with status ${response.status}`);
  }
}
