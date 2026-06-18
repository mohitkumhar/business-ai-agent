/**
 * Regression tests for dashboard/src/lib/mockPeriod.ts
 *
 * Clock is pinned to 2026-06-18 via jest.useFakeTimers() so every assertion
 * is deterministic. All 10 fixture transactions are dated in March 2026, which
 * produces three distinct filtering regimes:
 *   "this_month" (2026-06-01 → 2026-06-18) → 0 matching transactions
 *   "last_month" (2026-05-01 → 2026-05-31) → 0 matching transactions
 *   "ytd"        (2026-01-01 → 2026-06-18) → all 10 transactions
 *
 * Zero-transaction periods exercise every empty-state fallback branch.
 * No module mocks needed — all dependencies are pure data or date helpers.
 */

import {
  filterTransactionsByPeriod,
  mockSummaryForPeriod,
  mockRevenueVsExpenseForPeriod,
  mockSalesTrendForPeriod,
  mockFinancialOverviewForPeriod,
  mockSalesTargetForPeriod,
  mockAlertsForPeriod,
} from "../mockPeriod";
import {
  mockSummary,
  mockTransactions,
  mockSalesTrend,
  mockFinancialOverview,
  mockSalesTarget,
  mockAlertsBySeverity,
} from "../mockData";

// UTC noon on 2026-06-18 stays in June regardless of the runner's local offset.
const FIXED_DATE = new Date("2026-06-18T12:00:00.000Z");

beforeAll(() => {
  jest.useFakeTimers();
  jest.setSystemTime(FIXED_DATE);
});

afterAll(() => {
  jest.useRealTimers();
});

const ALL_TX = mockTransactions.transactions;
const TOTAL_TX_COUNT = ALL_TX.length; // 10

const TOTAL_REVENUE = ALL_TX.filter((t) => t.type === "Revenue").reduce(
  (sum, t) => sum + t.amount,
  0
); // 19_350

const TOTAL_EXPENSES = ALL_TX.filter((t) => t.type === "Expense").reduce(
  (sum, t) => sum + t.amount,
  0
); // 16_840

describe("filterTransactionsByPeriod", () => {
  it("always returns an array", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      expect(Array.isArray(filterTransactionsByPeriod(p))).toBe(true);
    });
  });

  it("ytd – returns all 10 transactions (March 2026 falls within Jan–Jun 2026)", () => {
    expect(filterTransactionsByPeriod("ytd")).toHaveLength(TOTAL_TX_COUNT);
  });

  it("this_month – returns an empty array (no transactions in June 2026)", () => {
    expect(filterTransactionsByPeriod("this_month")).toHaveLength(0);
  });

  it("last_month – returns an empty array (no transactions in May 2026)", () => {
    expect(filterTransactionsByPeriod("last_month")).toHaveLength(0);
  });

  it("ytd – every returned transaction is dated within 2026-01-01 … 2026-06-18", () => {
    filterTransactionsByPeriod("ytd").forEach((t) => {
      expect(t.transaction_date >= "2026-01-01").toBe(true);
      expect(t.transaction_date <= "2026-06-18").toBe(true);
    });
  });

  it("ytd – transactions preserve all required fields with correct types", () => {
    filterTransactionsByPeriod("ytd").forEach((t) => {
      expect(typeof t.transaction_id).toBe("number");
      expect(typeof t.transaction_date).toBe("string");
      expect(typeof t.type).toBe("string");
      expect(typeof t.category).toBe("string");
      expect(typeof t.amount).toBe("number");
      expect(typeof t.description).toBe("string");
    });
  });

  it("ytd – transaction_date strings match YYYY-MM-DD format", () => {
    filterTransactionsByPeriod("ytd").forEach((t) => {
      expect(t.transaction_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });
  });

  it("ytd – type is exclusively 'Revenue' or 'Expense'", () => {
    filterTransactionsByPeriod("ytd").forEach((t) => {
      expect(["Revenue", "Expense"]).toContain(t.type);
    });
  });

  it("ytd – amounts are all positive numbers", () => {
    filterTransactionsByPeriod("ytd").forEach((t) => {
      expect(t.amount).toBeGreaterThan(0);
    });
  });
});

describe("mockSummaryForPeriod", () => {
  const REQUIRED_KEYS = [
    "total_revenue",
    "total_expenses",
    "net_profit",
    "total_transactions",
    "active_alerts",
    "revenue_change",
    "expenses_change",
    "net_profit_change",
    "transactions_change",
  ] as const;

  it("returns an object with all required DashboardSummary keys for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const s = mockSummaryForPeriod(p);
      REQUIRED_KEYS.forEach((k) => expect(s).toHaveProperty(k));
    });
  });

  it("change fields are always 0 – not computed in this layer", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const s = mockSummaryForPeriod(p);
      expect(s.revenue_change).toBe(0);
      expect(s.expenses_change).toBe(0);
      expect(s.net_profit_change).toBe(0);
      expect(s.transactions_change).toBe(0);
    });
  });

  describe("ytd – all 10 transactions in range", () => {
    let s: ReturnType<typeof mockSummaryForPeriod>;

    beforeAll(() => { s = mockSummaryForPeriod("ytd"); });

    it("total_revenue sums all Revenue transaction amounts", () => {
      expect(s.total_revenue).toBe(TOTAL_REVENUE);
    });

    it("total_expenses sums all Expense transaction amounts", () => {
      expect(s.total_expenses).toBe(TOTAL_EXPENSES);
    });

    it("net_profit equals total_revenue − total_expenses", () => {
      expect(s.net_profit).toBe(s.total_revenue - s.total_expenses);
    });

    it("total_transactions is 10", () => {
      expect(s.total_transactions).toBe(TOTAL_TX_COUNT);
    });

    it("active_alerts is a non-negative integer", () => {
      expect(s.active_alerts).toBeGreaterThanOrEqual(0);
      expect(Number.isInteger(s.active_alerts)).toBe(true);
    });

    it("active_alerts equals mockSummary.active_alerts when scale factor is 1 (10/10)", () => {
      expect(s.active_alerts).toBe(mockSummary.active_alerts);
    });
  });

  describe("this_month – no transactions in June 2026", () => {
    let s: ReturnType<typeof mockSummaryForPeriod>;

    beforeAll(() => { s = mockSummaryForPeriod("this_month"); });

    it("total_revenue is 0", () => expect(s.total_revenue).toBe(0));
    it("total_expenses is 0", () => expect(s.total_expenses).toBe(0));
    it("net_profit is 0", () => expect(s.net_profit).toBe(0));
    it("total_transactions is 0", () => expect(s.total_transactions).toBe(0));

    it("active_alerts is 0 (scale = 0/10 = 0 → Math.round(12 × 0) = 0)", () => {
      expect(s.active_alerts).toBe(0);
    });
  });

  describe("last_month – no transactions in May 2026", () => {
    it("mirrors this_month results when no transactions fall in range", () => {
      const lm = mockSummaryForPeriod("last_month");
      expect(lm.total_revenue).toBe(0);
      expect(lm.total_expenses).toBe(0);
      expect(lm.net_profit).toBe(0);
      expect(lm.total_transactions).toBe(0);
      expect(lm.active_alerts).toBe(0);
    });
  });
});

describe("mockRevenueVsExpenseForPeriod", () => {
  it("returns an object with labels, revenue, and expenses arrays for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const r = mockRevenueVsExpenseForPeriod(p);
      expect(Array.isArray(r.labels)).toBe(true);
      expect(Array.isArray(r.revenue)).toBe(true);
      expect(Array.isArray(r.expenses)).toBe(true);
    });
  });

  it("labels, revenue, and expenses arrays are always the same length", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const r = mockRevenueVsExpenseForPeriod(p);
      expect(r.revenue).toHaveLength(r.labels.length);
      expect(r.expenses).toHaveLength(r.labels.length);
    });
  });

  describe("empty-period fallback – this_month (0 transactions)", () => {
    let r: ReturnType<typeof mockRevenueVsExpenseForPeriod>;

    beforeAll(() => { r = mockRevenueVsExpenseForPeriod("this_month"); });

    it("returns exactly one sentinel label", () => {
      expect(r.labels).toEqual(["No transactions in this period"]);
    });

    it("revenue sentinel is [1] and expenses sentinel is [0]", () => {
      expect(r.revenue).toEqual([1]);
      expect(r.expenses).toEqual([0]);
    });
  });

  describe("empty-period fallback – last_month (0 transactions)", () => {
    it("returns the same sentinel as this_month", () => {
      const r = mockRevenueVsExpenseForPeriod("last_month");
      expect(r.labels).toEqual(["No transactions in this period"]);
      expect(r.revenue).toEqual([1]);
      expect(r.expenses).toEqual([0]);
    });
  });

  describe("ytd – all 10 transactions in range", () => {
    let r: ReturnType<typeof mockRevenueVsExpenseForPeriod>;

    beforeAll(() => { r = mockRevenueVsExpenseForPeriod("ytd"); });

    it("does not include the sentinel label", () => {
      expect(r.labels).not.toContain("No transactions in this period");
    });

    it("labels are sorted alphabetically", () => {
      expect(r.labels).toEqual([...r.labels].sort());
    });

    it("contains exactly the 8 categories present in the fixture transactions", () => {
      expect(r.labels).toEqual([
        "Consulting",
        "Marketing",
        "Office",
        "Payroll",
        "Product Sales",
        "Software",
        "Subscriptions",
        "Travel",
      ]);
    });

    it("revenue values per category sum to TOTAL_REVENUE", () => {
      expect(r.revenue.reduce((a, b) => a + b, 0)).toBe(TOTAL_REVENUE);
    });

    it("expense values per category sum to TOTAL_EXPENSES", () => {
      expect(r.expenses.reduce((a, b) => a + b, 0)).toBe(TOTAL_EXPENSES);
    });

    it("no category carries both a positive revenue and a positive expense", () => {
      // In the fixture, every category is exclusively revenue or expense — never mixed.
      // This test would catch any future data change that blurs that boundary.
      r.labels.forEach((_, i) => {
        expect(r.revenue[i] > 0 && r.expenses[i] > 0).toBe(false);
      });
    });

    it("all revenue and expense values are non-negative", () => {
      r.revenue.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
      r.expenses.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
    });
  });
});

describe("mockSalesTrendForPeriod", () => {
  it("returns an object with labels, revenue, and expenses arrays for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const t = mockSalesTrendForPeriod(p);
      expect(Array.isArray(t.labels)).toBe(true);
      expect(Array.isArray(t.revenue)).toBe(true);
      expect(Array.isArray(t.expenses)).toBe(true);
    });
  });

  it("labels, revenue, and expenses arrays are always the same length", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const t = mockSalesTrendForPeriod(p);
      expect(t.revenue).toHaveLength(t.labels.length);
      expect(t.expenses).toHaveLength(t.labels.length);
    });
  });

  describe("empty-period fallback – this_month (0 transactions)", () => {
    it("returns the static mockSalesTrend verbatim", () => {
      const t = mockSalesTrendForPeriod("this_month");
      expect(t.labels).toEqual(mockSalesTrend.labels);
      expect(t.revenue).toEqual(mockSalesTrend.revenue);
      expect(t.expenses).toEqual(mockSalesTrend.expenses);
    });
  });

  describe("empty-period fallback – last_month (0 transactions)", () => {
    it("also returns the static mockSalesTrend", () => {
      const t = mockSalesTrendForPeriod("last_month");
      expect(t.labels).toEqual(mockSalesTrend.labels);
      expect(t.revenue).toEqual(mockSalesTrend.revenue);
      expect(t.expenses).toEqual(mockSalesTrend.expenses);
    });
  });

  describe("ytd – all 10 transactions produce 6 unique calendar dates", () => {
    let t: ReturnType<typeof mockSalesTrendForPeriod>;

    beforeAll(() => { t = mockSalesTrendForPeriod("ytd"); });

    it("has exactly 6 entries – one per unique transaction date (2026-03-23 … 2026-03-28)", () => {
      expect(t.labels).toHaveLength(6);
      expect(t.revenue).toHaveLength(6);
      expect(t.expenses).toHaveLength(6);
    });

    it("total revenue across all days equals TOTAL_REVENUE", () => {
      expect(t.revenue.reduce((a, b) => a + b, 0)).toBe(TOTAL_REVENUE);
    });

    it("total expenses across all days equals TOTAL_EXPENSES", () => {
      expect(t.expenses.reduce((a, b) => a + b, 0)).toBe(TOTAL_EXPENSES);
    });

    it("all revenue and expense values are non-negative", () => {
      t.revenue.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
      t.expenses.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
    });

    it("labels are non-empty strings (locale-formatted by toLocaleDateString)", () => {
      // Exact format varies by Node.js locale; only the type is asserted here.
      t.labels.forEach((l) => {
        expect(typeof l).toBe("string");
        expect(l.length).toBeGreaterThan(0);
      });
    });

    it("does not fall back to the static mockSalesTrend labels", () => {
      expect(t.labels).not.toEqual(mockSalesTrend.labels);
    });
  });
});

describe("mockFinancialOverviewForPeriod", () => {
  it("returns an object with all five required arrays for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const f = mockFinancialOverviewForPeriod(p);
      ["labels", "revenue", "expenses", "net_profit", "cash_balance"].forEach((k) =>
        expect(f).toHaveProperty(k)
      );
    });
  });

  it("all five arrays have the same length for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const f = mockFinancialOverviewForPeriod(p);
      const len = f.labels.length;
      expect(f.revenue).toHaveLength(len);
      expect(f.expenses).toHaveLength(len);
      expect(f.net_profit).toHaveLength(len);
      expect(f.cash_balance).toHaveLength(len);
    });
  });

  describe("this_month – June 2026", () => {
    let f: ReturnType<typeof mockFinancialOverviewForPeriod>;

    beforeAll(() => { f = mockFinancialOverviewForPeriod("this_month"); });

    it("returns exactly 1 month", () => {
      expect(f.labels).toHaveLength(1);
    });

    it("the single label is '2026-06'", () => {
      expect(f.labels[0]).toBe("2026-06");
    });

    it("values match the June entry in mockFinancialOverview", () => {
      const idx = mockFinancialOverview.labels.indexOf("2026-06");
      expect(f.revenue[0]).toBe(mockFinancialOverview.revenue[idx]);
      expect(f.expenses[0]).toBe(mockFinancialOverview.expenses[idx]);
      expect(f.net_profit[0]).toBe(mockFinancialOverview.net_profit[idx]);
      expect(f.cash_balance[0]).toBe(mockFinancialOverview.cash_balance[idx]);
    });
  });

  describe("last_month – May 2026", () => {
    let f: ReturnType<typeof mockFinancialOverviewForPeriod>;

    beforeAll(() => { f = mockFinancialOverviewForPeriod("last_month"); });

    it("returns exactly 1 month", () => {
      expect(f.labels).toHaveLength(1);
    });

    it("the single label is '2026-05'", () => {
      expect(f.labels[0]).toBe("2026-05");
    });

    it("values match the May entry in mockFinancialOverview", () => {
      const idx = mockFinancialOverview.labels.indexOf("2026-05");
      expect(f.revenue[0]).toBe(mockFinancialOverview.revenue[idx]);
      expect(f.expenses[0]).toBe(mockFinancialOverview.expenses[idx]);
      expect(f.net_profit[0]).toBe(mockFinancialOverview.net_profit[idx]);
      expect(f.cash_balance[0]).toBe(mockFinancialOverview.cash_balance[idx]);
    });
  });

  describe("ytd – January through June 2026", () => {
    let f: ReturnType<typeof mockFinancialOverviewForPeriod>;

    beforeAll(() => { f = mockFinancialOverviewForPeriod("ytd"); });

    it("returns 6 months", () => {
      expect(f.labels).toHaveLength(6);
    });

    it("first label is '2026-01' and last is '2026-06'", () => {
      expect(f.labels[0]).toBe("2026-01");
      expect(f.labels[5]).toBe("2026-06");
    });

    it("all labels match YYYY-MM format", () => {
      f.labels.forEach((l) => expect(l).toMatch(/^\d{4}-\d{2}$/));
    });

    it("labels are in chronological order", () => {
      for (let i = 1; i < f.labels.length; i++) {
        expect(f.labels[i] > f.labels[i - 1]).toBe(true);
      }
    });

    it("revenue, expenses, and net_profit values match the first 6 entries of mockFinancialOverview", () => {
      expect(f.revenue).toEqual(mockFinancialOverview.revenue.slice(0, 6));
      expect(f.expenses).toEqual(mockFinancialOverview.expenses.slice(0, 6));
      expect(f.net_profit).toEqual(mockFinancialOverview.net_profit.slice(0, 6));
    });
  });
});

describe("mockSalesTargetForPeriod", () => {
  it("returns an object with business_name, current_revenue, target_revenue, percentage", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const s = mockSalesTargetForPeriod(p);
      expect(s).toHaveProperty("business_name");
      expect(s).toHaveProperty("current_revenue");
      expect(s).toHaveProperty("target_revenue");
      expect(s).toHaveProperty("percentage");
    });
  });

  it("business_name matches the source fixture for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      expect(mockSalesTargetForPeriod(p).business_name).toBe(mockSalesTarget.business_name);
    });
  });

  it("percentage is clamped between 0 and 100 for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const pct = mockSalesTargetForPeriod(p).percentage;
      expect(pct).toBeGreaterThanOrEqual(0);
      expect(pct).toBeLessThanOrEqual(100);
    });
  });

  describe("this_month – no Revenue transactions in June 2026", () => {
    let s: ReturnType<typeof mockSalesTargetForPeriod>;

    beforeAll(() => { s = mockSalesTargetForPeriod("this_month"); });

    it("current_revenue is 0", () => expect(s.current_revenue).toBe(0));
    it("target_revenue equals the monthly target from fixture", () => {
      expect(s.target_revenue).toBe(mockSalesTarget.target_revenue);
    });
    it("percentage is 0", () => expect(s.percentage).toBe(0));
  });

  describe("last_month – no Revenue transactions in May 2026", () => {
    it("mirrors this_month results", () => {
      const lm = mockSalesTargetForPeriod("last_month");
      expect(lm.current_revenue).toBe(0);
      expect(lm.target_revenue).toBe(mockSalesTarget.target_revenue);
      expect(lm.percentage).toBe(0);
    });
  });

  describe("ytd – all Revenue transactions in scope", () => {
    let s: ReturnType<typeof mockSalesTargetForPeriod>;

    beforeAll(() => { s = mockSalesTargetForPeriod("ytd"); });

    it("current_revenue equals the sum of all Revenue transactions", () => {
      expect(s.current_revenue).toBe(TOTAL_REVENUE);
    });

    it("target_revenue equals monthlyTarget × months-elapsed (400 000 × 6 = 2 400 000)", () => {
      // now.getMonth() returns 5 for June (0-indexed) → monthsElapsed = 6
      expect(s.target_revenue).toBe(mockSalesTarget.target_revenue * 6);
    });

    it("percentage has at most one decimal place (Math.round(x × 1000) / 10)", () => {
      const str = String(s.percentage);
      const decimals = str.includes(".") ? str.split(".")[1].length : 0;
      expect(decimals).toBeLessThanOrEqual(1);
    });

    it("percentage is 0.8 (19 350 / 2 400 000 × 100, rounded to 1 dp)", () => {
      expect(s.percentage).toBe(0.8);
    });
  });
});

describe("mockAlertsForPeriod", () => {
  it("returns an object with labels and data arrays for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const a = mockAlertsForPeriod(p);
      expect(Array.isArray(a.labels)).toBe(true);
      expect(Array.isArray(a.data)).toBe(true);
    });
  });

  it("labels always equal mockAlertsBySeverity.labels (never scaled)", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      expect(mockAlertsForPeriod(p).labels).toEqual(mockAlertsBySeverity.labels);
    });
  });

  it("data length matches labels length for every period", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      const a = mockAlertsForPeriod(p);
      expect(a.data).toHaveLength(a.labels.length);
    });
  });

  it("all data values are non-negative integers", () => {
    (["ytd", "this_month", "last_month"] as const).forEach((p) => {
      mockAlertsForPeriod(p).data.forEach((v) => {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(Number.isInteger(v)).toBe(true);
      });
    });
  });

  it("this_month – scale=0 falls back to f=1 via (scale || 1); data is unchanged", () => {
    // When no transactions match, scale = 0/10 = 0. Since 0 is falsy,
    // (scale || 1) evaluates to 1, so the scale factor is never truly zero.
    // This means zero-transaction periods produce the same alert counts as scale=1.
    const a = mockAlertsForPeriod("this_month");
    expect(a.data).toEqual(
      mockAlertsBySeverity.data.map((n) => Math.max(0, Math.round(n * 1)))
    );
  });

  it("last_month – same (scale || 1) fallback produces identical data to this_month", () => {
    expect(mockAlertsForPeriod("last_month").data).toEqual(
      mockAlertsForPeriod("this_month").data
    );
  });

  it("ytd – scale=1, data equals source values after rounding", () => {
    const a = mockAlertsForPeriod("ytd");
    expect(a.data).toEqual(
      mockAlertsBySeverity.data.map((n) => Math.max(0, Math.round(n * 1)))
    );
  });
});