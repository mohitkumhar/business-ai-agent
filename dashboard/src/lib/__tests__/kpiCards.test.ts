/**
 * Regression tests for dashboard/src/lib/kpiCards.tsx
 *
 * Strategy:
 *  - buildKpiCards is a pure function over DashboardSummary + a loading flag.
 *  - Verify the empty-data case, the card count/order/labels, the loading
 *    placeholder values, and the "positive" sign logic for each card
 *    (including the inverted logic for expenses).
 */
import { buildKpiCards } from "../kpiCards";
import type { DashboardSummary } from "../api";

const baseSummary: DashboardSummary = {
  total_revenue: 500000,
  total_expenses: 200000,
  net_profit: 300000,
  total_transactions: 1234,
  active_alerts: 2,
  revenue_change: 5,
  expenses_change: -3,
  net_profit_change: 8,
  transactions_change: 1.5,
};

describe("buildKpiCards", () => {
  it("returns an empty array when there is no data", () => {
    expect(buildKpiCards(null, false)).toEqual([]);
  });

  it("returns five cards in a fixed order when data is present", () => {
    const cards = buildKpiCards(baseSummary, false);
    expect(cards).toHaveLength(5);
    expect(cards.map((c) => c.label)).toEqual([
      "Total Revenue",
      "Total Expenses",
      "Net Profit",
      "Transactions",
      "Active Alerts",
    ]);
  });

  it("shows loading placeholders for revenue/expenses/transactions while loading", () => {
    const cards = buildKpiCards(baseSummary, true);
    const byLabel = Object.fromEntries(cards.map((c) => [c.label, c]));

    expect(byLabel["Total Revenue"].value).toBe("...");
    expect(byLabel["Total Revenue"].change).toBe("0%");
    expect(byLabel["Total Expenses"].value).toBe("...");
    expect(byLabel["Transactions"].change).toBe("0%");
  });

  it("treats positive revenue change as positive", () => {
    const cards = buildKpiCards(baseSummary, false);
    const revenue = cards.find((c) => c.label === "Total Revenue")!;
    expect(revenue.positive).toBe(true);
    expect(revenue.change).toBe("5%");
  });

  it("treats a decrease in expenses as positive (inverted logic)", () => {
    const cards = buildKpiCards(baseSummary, false);
    const expenses = cards.find((c) => c.label === "Total Expenses")!;
    expect(expenses.positive).toBe(true);
    expect(expenses.change).toBe("-3%");
  });

  it("treats an increase in expenses as not positive", () => {
    const summary = { ...baseSummary, expenses_change: 4 };
    const cards = buildKpiCards(summary, false);
    const expenses = cards.find((c) => c.label === "Total Expenses")!;
    expect(expenses.positive).toBe(false);
  });

  it("formats net profit using formatCurrency (INR bands)", () => {
    const cards = buildKpiCards(baseSummary, false);
    const netProfit = cards.find((c) => c.label === "Net Profit")!;
    expect(netProfit.value).toBe("₹3.00 L");
  });

  it("formats transaction count using formatNumber", () => {
    const cards = buildKpiCards(baseSummary, false);
    const transactions = cards.find((c) => c.label === "Transactions")!;
    expect(transactions.value).toBe("1.2K");
  });

  it("has an empty change and non-positive flag for the Active Alerts card", () => {
    const cards = buildKpiCards(baseSummary, false);
    const alerts = cards.find((c) => c.label === "Active Alerts")!;
    expect(alerts.change).toBe("");
    expect(alerts.positive).toBe(false);
    expect(alerts.value).toBe("2");
  });

  it("defaults missing/zero fields to sensible fallbacks", () => {
    const sparse: DashboardSummary = {
      total_revenue: 0,
      total_expenses: 0,
      net_profit: 0,
      total_transactions: 0,
      active_alerts: 0,
      revenue_change: 0,
      expenses_change: 0,
      net_profit_change: 0,
      transactions_change: 0,
    };
    const cards = buildKpiCards(sparse, false);
    expect(cards.find((c) => c.label === "Net Profit")!.value).toBe("₹0");
    expect(cards.find((c) => c.label === "Active Alerts")!.value).toBe("0");
  });
});