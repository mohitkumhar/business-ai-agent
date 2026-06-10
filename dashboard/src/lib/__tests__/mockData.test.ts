/**
 * Regression tests for dashboard/src/lib/mockData.ts
 *
 * Strategy:
 *  - No module mocks needed — mockData.ts is pure static/computed data.
 *  - Import every named export and assert structural integrity, array-length
 *    consistency, mathematical invariants, and data-validity constraints.
 *  - For mockForecast (the only dynamically-generated export), additionally
 *    verify item counts, date ordering, and bound relationships.
 */

import {
  mockSummary,
  mockFinancialOverview,
  mockSalesTarget,
  mockTransactions,
  mockCategories,
  mockRevenueVsExpense,
  mockSalesTrend,
  mockAlertsBySeverity,
  mockHealthScores,
  mockTopProducts,
  mockEmployeeStats,
  mockForecast,
} from "../mockData";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Returns true when s is a calendar date in YYYY-MM-DD format. */
function isDateString(s: unknown): boolean {
  if (typeof s !== "string") return false;
  return /^\d{4}-\d{2}-\d{2}$/.test(s) && !isNaN(Date.parse(s));
}

// ---------------------------------------------------------------------------
// mockSummary
// ---------------------------------------------------------------------------

describe("mockSummary", () => {
  it("is defined and exported", () => {
    expect(mockSummary).toBeDefined();
  });

  it("has all required DashboardSummary keys", () => {
    const keys: (keyof typeof mockSummary)[] = [
      "total_revenue",
      "total_expenses",
      "net_profit",
      "total_transactions",
      "active_alerts",
      "revenue_change",
      "expenses_change",
      "net_profit_change",
      "transactions_change",
    ];
    keys.forEach((k) => expect(mockSummary).toHaveProperty(k));
  });

  it("net_profit equals total_revenue minus total_expenses", () => {
    expect(mockSummary.net_profit).toBe(
      mockSummary.total_revenue - mockSummary.total_expenses
    );
  });

  it("all numeric values are positive", () => {
    expect(mockSummary.total_revenue).toBeGreaterThan(0);
    expect(mockSummary.total_expenses).toBeGreaterThan(0);
    expect(mockSummary.net_profit).toBeGreaterThan(0);
    expect(mockSummary.total_transactions).toBeGreaterThan(0);
  });

  it("active_alerts is a non-negative integer", () => {
    expect(mockSummary.active_alerts).toBeGreaterThanOrEqual(0);
    expect(Number.isInteger(mockSummary.active_alerts)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// mockFinancialOverview
// ---------------------------------------------------------------------------

describe("mockFinancialOverview", () => {
  it("is defined and exported", () => {
    expect(mockFinancialOverview).toBeDefined();
  });

  it("labels, revenue, expenses, net_profit, and cash_balance all have 12 entries", () => {
    expect(mockFinancialOverview.labels).toHaveLength(12);
    expect(mockFinancialOverview.revenue).toHaveLength(12);
    expect(mockFinancialOverview.expenses).toHaveLength(12);
    expect(mockFinancialOverview.net_profit).toHaveLength(12);
    expect(mockFinancialOverview.cash_balance).toHaveLength(12);
  });

  it("labels are in YYYY-MM month format", () => {
    mockFinancialOverview.labels.forEach((label) => {
      expect(label).toMatch(/^\d{4}-\d{2}$/);
    });
  });

  it("net_profit[i] equals revenue[i] minus expenses[i] for every month", () => {
    const { revenue, expenses, net_profit } = mockFinancialOverview;
    revenue.forEach((rev, i) => {
      expect(net_profit[i]).toBe(rev - expenses[i]);
    });
  });

  it("cash_balance is monotonically increasing", () => {
    const { cash_balance } = mockFinancialOverview;
    for (let i = 1; i < cash_balance.length; i++) {
      expect(cash_balance[i]).toBeGreaterThan(cash_balance[i - 1]);
    }
  });

  it("all revenue and expense values are positive", () => {
    mockFinancialOverview.revenue.forEach((v) => expect(v).toBeGreaterThan(0));
    mockFinancialOverview.expenses.forEach((v) => expect(v).toBeGreaterThan(0));
  });
});

// ---------------------------------------------------------------------------
// mockSalesTarget
// ---------------------------------------------------------------------------

describe("mockSalesTarget", () => {
  it("is defined and exported", () => {
    expect(mockSalesTarget).toBeDefined();
  });

  it("has all required SalesTarget keys", () => {
    expect(mockSalesTarget).toHaveProperty("business_name");
    expect(mockSalesTarget).toHaveProperty("current_revenue");
    expect(mockSalesTarget).toHaveProperty("target_revenue");
    expect(mockSalesTarget).toHaveProperty("percentage");
  });

  it("percentage approximates (current_revenue / target_revenue) * 100", () => {
    const computed =
      (mockSalesTarget.current_revenue / mockSalesTarget.target_revenue) * 100;
    expect(mockSalesTarget.percentage).toBeCloseTo(computed, 1);
  });

  it("percentage is between 0 and 100 (target not yet reached)", () => {
    expect(mockSalesTarget.percentage).toBeGreaterThan(0);
    expect(mockSalesTarget.percentage).toBeLessThan(100);
  });

  it("business_name is a non-empty string", () => {
    expect(typeof mockSalesTarget.business_name).toBe("string");
    expect(mockSalesTarget.business_name.length).toBeGreaterThan(0);
  });

  it("current_revenue is less than target_revenue", () => {
    expect(mockSalesTarget.current_revenue).toBeLessThan(
      mockSalesTarget.target_revenue
    );
  });
});

// ---------------------------------------------------------------------------
// mockCategories
// ---------------------------------------------------------------------------

describe("mockCategories", () => {
  it("is defined and exported", () => {
    expect(mockCategories).toBeDefined();
  });

  it("has a categories array", () => {
    expect(Array.isArray(mockCategories.categories)).toBe(true);
  });

  it("contains exactly 8 category strings", () => {
    expect(mockCategories.categories).toHaveLength(8);
  });

  it("all entries are non-empty strings", () => {
    mockCategories.categories.forEach((c) => {
      expect(typeof c).toBe("string");
      expect(c.length).toBeGreaterThan(0);
    });
  });

  it("has no duplicate categories", () => {
    const unique = new Set(mockCategories.categories);
    expect(unique.size).toBe(mockCategories.categories.length);
  });
});

// ---------------------------------------------------------------------------
// mockTransactions
// ---------------------------------------------------------------------------

describe("mockTransactions", () => {
  it("is defined and exported", () => {
    expect(mockTransactions).toBeDefined();
  });

  it("contains exactly 10 transactions", () => {
    expect(mockTransactions.transactions).toHaveLength(10);
  });

  it("all transaction_ids are unique", () => {
    const ids = mockTransactions.transactions.map((t) => t.transaction_id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("each transaction has all required fields with correct types", () => {
    mockTransactions.transactions.forEach((t) => {
      expect(typeof t.transaction_id).toBe("number");
      expect(typeof t.transaction_date).toBe("string");
      expect(typeof t.type).toBe("string");
      expect(typeof t.category).toBe("string");
      expect(typeof t.amount).toBe("number");
      expect(typeof t.description).toBe("string");
    });
  });

  it("transaction_date values are valid YYYY-MM-DD strings", () => {
    mockTransactions.transactions.forEach((t) => {
      expect(isDateString(t.transaction_date)).toBe(true);
    });
  });

  it("type is either Revenue or Expense", () => {
    const validTypes = ["Revenue", "Expense"];
    mockTransactions.transactions.forEach((t) => {
      expect(validTypes).toContain(t.type);
    });
  });

  it("all amounts are positive", () => {
    mockTransactions.transactions.forEach((t) => {
      expect(t.amount).toBeGreaterThan(0);
    });
  });

  it("all transaction categories belong to mockCategories", () => {
    const validCategories = new Set(mockCategories.categories);
    mockTransactions.transactions.forEach((t) => {
      expect(validCategories.has(t.category)).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// mockRevenueVsExpense
// ---------------------------------------------------------------------------

describe("mockRevenueVsExpense", () => {
  it("is defined and exported", () => {
    expect(mockRevenueVsExpense).toBeDefined();
  });

  it("labels, revenue, and expenses arrays all have the same length", () => {
    const len = mockRevenueVsExpense.labels.length;
    expect(mockRevenueVsExpense.revenue).toHaveLength(len);
    expect(mockRevenueVsExpense.expenses).toHaveLength(len);
  });

  it("has exactly 8 entries (one per category)", () => {
    expect(mockRevenueVsExpense.labels).toHaveLength(8);
  });

  it("revenue and expenses are mutually exclusive per index (no mixed rows)", () => {
    const { revenue, expenses } = mockRevenueVsExpense;
    revenue.forEach((rev, i) => {
      // At most one of revenue[i] or expenses[i] can be nonzero
      const bothNonZero = rev > 0 && expenses[i] > 0;
      expect(bothNonZero).toBe(false);
    });
  });

  it("all revenue and expense values are non-negative", () => {
    mockRevenueVsExpense.revenue.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
    mockRevenueVsExpense.expenses.forEach((v) => expect(v).toBeGreaterThanOrEqual(0));
  });
});

// ---------------------------------------------------------------------------
// mockSalesTrend
// ---------------------------------------------------------------------------

describe("mockSalesTrend", () => {
  it("is defined and exported", () => {
    expect(mockSalesTrend).toBeDefined();
  });

  it("labels, revenue, and expenses all have 7 entries (one per weekday)", () => {
    expect(mockSalesTrend.labels).toHaveLength(7);
    expect(mockSalesTrend.revenue).toHaveLength(7);
    expect(mockSalesTrend.expenses).toHaveLength(7);
  });

  it("all revenue values are positive", () => {
    mockSalesTrend.revenue.forEach((v) => expect(v).toBeGreaterThan(0));
  });

  it("all expense values are positive", () => {
    mockSalesTrend.expenses.forEach((v) => expect(v).toBeGreaterThan(0));
  });
});

// ---------------------------------------------------------------------------
// mockAlertsBySeverity
// ---------------------------------------------------------------------------

describe("mockAlertsBySeverity", () => {
  it("is defined and exported", () => {
    expect(mockAlertsBySeverity).toBeDefined();
  });

  it("has exactly 3 severity labels", () => {
    expect(mockAlertsBySeverity.labels).toHaveLength(3);
  });

  it("labels are Critical, Warning, Info in that order", () => {
    expect(mockAlertsBySeverity.labels).toEqual(["Critical", "Warning", "Info"]);
  });

  it("data array has the same length as labels", () => {
    expect(mockAlertsBySeverity.data).toHaveLength(
      mockAlertsBySeverity.labels.length
    );
  });

  it("all data values are non-negative integers", () => {
    mockAlertsBySeverity.data.forEach((v) => {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(Number.isInteger(v)).toBe(true);
    });
  });
});

// ---------------------------------------------------------------------------
// mockHealthScores
// ---------------------------------------------------------------------------

describe("mockHealthScores", () => {
  it("is defined and exported", () => {
    expect(mockHealthScores).toBeDefined();
  });

  it("businesses and scores arrays have the same length", () => {
    expect(mockHealthScores.scores).toHaveLength(
      mockHealthScores.businesses.length
    );
  });

  it("each score name matches the corresponding business name", () => {
    mockHealthScores.scores.forEach((score, i) => {
      expect(score.name).toBe(mockHealthScores.businesses[i]);
    });
  });

  it("all numeric score fields are between 0 and 100", () => {
    const numericFields = [
      "overall",
      "cash",
      "profitability",
      "growth",
      "cost_control",
      "risk",
    ] as const;
    mockHealthScores.scores.forEach((score) => {
      numericFields.forEach((field) => {
        expect(score[field]).toBeGreaterThanOrEqual(0);
        expect(score[field]).toBeLessThanOrEqual(100);
      });
    });
  });
});

// ---------------------------------------------------------------------------
// mockTopProducts
// ---------------------------------------------------------------------------

describe("mockTopProducts", () => {
  it("is defined and exported", () => {
    expect(mockTopProducts).toBeDefined();
  });

  it("labels, stock, margin, margin_amount, and margin_pct all have 6 entries", () => {
    const len = mockTopProducts.labels.length;
    expect(len).toBe(6);
    expect(mockTopProducts.stock).toHaveLength(len);
    expect(mockTopProducts.margin).toHaveLength(len);
    expect(mockTopProducts.margin_amount).toHaveLength(len);
    expect(mockTopProducts.margin_pct).toHaveLength(len);
  });

  it("margin_pct equals margin element-by-element", () => {
    mockTopProducts.margin.forEach((m, i) => {
      expect(mockTopProducts.margin_pct![i]).toBe(m);
    });
  });

  it("all stock values are positive integers", () => {
    mockTopProducts.stock.forEach((v) => {
      expect(v).toBeGreaterThan(0);
      expect(Number.isInteger(v)).toBe(true);
    });
  });

  it("all margin percentages are between 0 and 100", () => {
    mockTopProducts.margin.forEach((v) => {
      expect(v).toBeGreaterThan(0);
      expect(v).toBeLessThanOrEqual(100);
    });
  });
});

// ---------------------------------------------------------------------------
// mockEmployeeStats
// ---------------------------------------------------------------------------

describe("mockEmployeeStats", () => {
  it("is defined and exported", () => {
    expect(mockEmployeeStats).toBeDefined();
  });

  it("labels, counts, and avg_salary all have 6 entries", () => {
    expect(mockEmployeeStats.labels).toHaveLength(6);
    expect(mockEmployeeStats.counts).toHaveLength(6);
    expect(mockEmployeeStats.avg_salary).toHaveLength(6);
  });

  it("all department head counts are positive integers", () => {
    mockEmployeeStats.counts.forEach((c) => {
      expect(c).toBeGreaterThan(0);
      expect(Number.isInteger(c)).toBe(true);
    });
  });

  it("all average salaries are positive", () => {
    mockEmployeeStats.avg_salary.forEach((s) => expect(s).toBeGreaterThan(0));
  });
});

// ---------------------------------------------------------------------------
// mockForecast  (dynamic — generated at module load time)
// ---------------------------------------------------------------------------

describe("mockForecast", () => {
  it("is defined and exported", () => {
    expect(mockForecast).toBeDefined();
  });

  // ── historical ────────────────────────────────────────────────────────────

  describe("historical data", () => {
    it("contains exactly 60 data points", () => {
      expect(mockForecast.historical).toHaveLength(60);
    });

    it("every item has a valid YYYY-MM-DD date string", () => {
      mockForecast.historical.forEach((item) => {
        expect(isDateString(item.date)).toBe(true);
      });
    });

    it("every item has a positive actual value", () => {
      mockForecast.historical.forEach((item) => {
        expect(item.actual).toBeGreaterThan(0);
      });
    });

    it("dates are in strictly ascending chronological order", () => {
      const { historical } = mockForecast;
      for (let i = 1; i < historical.length; i++) {
        expect(new Date(historical[i].date).getTime()).toBeGreaterThan(
          new Date(historical[i - 1].date).getTime()
        );
      }
    });
  });

  // ── forecast ──────────────────────────────────────────────────────────────

  describe("forecast data", () => {
    it("contains exactly 30 data points", () => {
      expect(mockForecast.forecast).toHaveLength(30);
    });

    it("every item has a valid YYYY-MM-DD date string", () => {
      mockForecast.forecast.forEach((item) => {
        expect(isDateString(item.date)).toBe(true);
      });
    });

    it("every item has positive predicted, lower_bound, and upper_bound", () => {
      mockForecast.forecast.forEach((item) => {
        expect(item.predicted).toBeGreaterThan(0);
        expect(item.lower_bound).toBeGreaterThan(0);
        expect(item.upper_bound).toBeGreaterThan(0);
      });
    });

    it("lower_bound < predicted < upper_bound for every forecast item", () => {
      mockForecast.forecast.forEach((item) => {
        expect(item.lower_bound).toBeLessThan(item.predicted);
        expect(item.upper_bound).toBeGreaterThan(item.predicted);
      });
    });

    it("predicted values are strictly increasing across the forecast window", () => {
      const { forecast } = mockForecast;
      for (let i = 1; i < forecast.length; i++) {
        expect(forecast[i].predicted).toBeGreaterThan(forecast[i - 1].predicted);
      }
    });

    it("dates are in strictly ascending chronological order", () => {
      const { forecast } = mockForecast;
      for (let i = 1; i < forecast.length; i++) {
        expect(new Date(forecast[i].date).getTime()).toBeGreaterThan(
          new Date(forecast[i - 1].date).getTime()
        );
      }
    });
  });

  // ── metadata ──────────────────────────────────────────────────────────────

  describe("metadata fields", () => {
    it("trend_direction is a valid ForecastTrend value", () => {
      const validTrends = ["up", "down", "flat"];
      expect(validTrends).toContain(mockForecast.trend_direction);
    });

    it("trend_direction is 'up'", () => {
      expect(mockForecast.trend_direction).toBe("up");
    });

    it("trend_percent is 12.5", () => {
      expect(mockForecast.trend_percent).toBe(12.5);
    });

    it("insight is a non-empty string", () => {
      expect(typeof mockForecast.insight).toBe("string");
      expect(mockForecast.insight.length).toBeGreaterThan(0);
    });
  });
});