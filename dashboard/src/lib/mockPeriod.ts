import type {
  DashboardSummary,
  RevenueVsExpense,
  SalesTrend,
  FinancialOverview,
  SalesTarget,
  Transaction,
} from "./api";
import type { DashboardPeriod } from "./dashboardPeriod";
import { getPeriodBounds } from "./dashboardPeriod";
import {
  mockSummary,
  mockTransactions,
  mockRevenueVsExpense,
  mockSalesTrend,
  mockFinancialOverview,
  mockSalesTarget,
  mockAlertsBySeverity,
} from "./mockData";

export function filterTransactionsByPeriod(period: DashboardPeriod): Transaction[] {
  const { start, end } = getPeriodBounds(period);
  return mockTransactions.transactions.filter(
    (t) => t.transaction_date >= start && t.transaction_date <= end
  );
}

export function mockSummaryForPeriod(period: DashboardPeriod): DashboardSummary {
  const tx = filterTransactionsByPeriod(period);
  let total_revenue = 0;
  let total_expenses = 0;
  for (const t of tx) {
    if (t.type === "Revenue") total_revenue += t.amount;
    else total_expenses += t.amount;
  }
  const n = tx.length;
  const scale =
    mockTransactions.transactions.length > 0
      ? n / mockTransactions.transactions.length
      : 1;
  return {
    total_revenue,
    total_expenses,
    net_profit: total_revenue - total_expenses,
    total_transactions: n,
    active_alerts: Math.max(0, Math.round(mockSummary.active_alerts * scale)),
    revenue_change: 0,
    expenses_change: 0,
    net_profit_change: 0,
    transactions_change: 0,
  };
}



export function mockRevenueVsExpenseForPeriod(period: DashboardPeriod): RevenueVsExpense {
  const tx = filterTransactionsByPeriod(period);
  const revenue: Record<string, number> = {};
  const expenses: Record<string, number> = {};
  for (const t of tx) {
    const cat = t.category || "Other";
    if (t.type === "Revenue") revenue[cat] = (revenue[cat] || 0) + t.amount;
    else expenses[cat] = (expenses[cat] || 0) + t.amount;
  }
  const allCats = [...new Set([...Object.keys(revenue), ...Object.keys(expenses)])].sort((a, b) => a - b);
  if (allCats.length === 0) {
    return {
      labels: ["No transactions in this period"],
      revenue: [1],
      expenses: [0],
    };
  }
  return {
    labels: allCats,
    revenue: allCats.map((c) => revenue[c] || 0),
    expenses: allCats.map((c) => expenses[c] || 0),
  };
}

export function mockSalesTrendForPeriod(period: DashboardPeriod): SalesTrend {
  const tx = filterTransactionsByPeriod(period);
  const byDay: Record<string, { revenue: number; expenses: number }> = {};
  for (const t of tx) {
    const day = t.transaction_date;
    if (!byDay[day]) byDay[day] = { revenue: 0, expenses: 0 };
    if (t.type === "Revenue") byDay[day].revenue += t.amount;
    else byDay[day].expenses += t.amount;
  }
  const days = Object.keys(byDay).sort();
  if (days.length === 0) {
    return { labels: mockSalesTrend.labels, revenue: mockSalesTrend.revenue, expenses: mockSalesTrend.expenses };
  }
  return {
    labels: days.map((d) => {
      const dt = new Date(d + "T12:00:00");
      return dt.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
    }),
    revenue: days.map((d) => byDay[d].revenue),
    expenses: days.map((d) => byDay[d].expenses),
  };
}

export function mockFinancialOverviewForPeriod(period: DashboardPeriod): FinancialOverview {
  const { start, end } = getPeriodBounds(period);
  const startYm = start.slice(0, 7);
  const endYm = end.slice(0, 7);
  const labels: string[] = [];
  const revenue: number[] = [];
  const expenses: number[] = [];
  const net_profit: number[] = [];
  const cash_balance: number[] = [];
  for (let i = 0; i < mockFinancialOverview.labels.length; i++) {
    const lab = mockFinancialOverview.labels[i];
    if (lab >= startYm && lab <= endYm) {
      labels.push(lab);
      revenue.push(mockFinancialOverview.revenue[i]);
      expenses.push(mockFinancialOverview.expenses[i]);
      net_profit.push(mockFinancialOverview.net_profit[i]);
      cash_balance.push(mockFinancialOverview.cash_balance[i]);
    }
  }
  if (labels.length === 0) {
    return {
      labels: mockFinancialOverview.labels.slice(0, 3),
      revenue: mockFinancialOverview.revenue.slice(0, 3),
      expenses: mockFinancialOverview.expenses.slice(0, 3),
      net_profit: mockFinancialOverview.net_profit.slice(0, 3),
      cash_balance: mockFinancialOverview.cash_balance.slice(0, 3),
    };
  }
  return { labels, revenue, expenses, net_profit, cash_balance };
}

export function mockSalesTargetForPeriod(period: DashboardPeriod): SalesTarget {
  const tx = filterTransactionsByPeriod(period);
  let current = 0;
  for (const t of tx) {
    if (t.type === "Revenue") current += t.amount;
  }
  const monthlyTarget = mockSalesTarget.target_revenue;
  const now = new Date();
  let displayTarget = monthlyTarget;
  let denom = monthlyTarget;
  if (period === "ytd") {
    const monthsElapsed = now.getMonth() + 1;
    denom = monthlyTarget * monthsElapsed;
    displayTarget = denom;
  }
  const pct =
    denom > 0 ? Math.min(100, Math.round((current / denom) * 1000) / 10) : 0;
  return {
    business_name: mockSalesTarget.business_name,
    current_revenue: current,
    target_revenue: displayTarget,
    percentage: pct,
  };
}

export function mockAlertsForPeriod(period: DashboardPeriod): typeof mockAlertsBySeverity {
  const scale = filterTransactionsByPeriod(period).length / Math.max(1, mockTransactions.transactions.length);
  const f = Math.max(0.3, Math.min(1.2, scale || 1));
  return {
    labels: mockAlertsBySeverity.labels,
    data: mockAlertsBySeverity.data.map((n) => Math.max(0, Math.round(n * f))),
  };
}
