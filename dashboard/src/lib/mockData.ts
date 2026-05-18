import type {
  DashboardSummary,
  FinancialOverview,
  SalesTarget,
  Transaction,
  RevenueVsExpense,
  SalesTrend,
  AlertsBySeverity,
  HealthScores,
  TopProducts,
  EmployeeStats,
  Forecast,
} from "./api";


export const mockSummary: DashboardSummary = {
  total_revenue: 284500,
  total_expenses: 142300,
  net_profit: 142200,
  total_transactions: 2847,
  active_alerts: 12,
  revenue_change: 12.5,
  expenses_change: 8.2,
  net_profit_change: 15.1,
  transactions_change: 4.3,
};


export const mockFinancialOverview: FinancialOverview = {
  labels: [
    "2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
    "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12",
  ],
  revenue: [18200, 21400, 19800, 24600, 22100, 26800, 28400, 31200, 27500, 25300, 23900, 29700],
  expenses: [12100, 14200, 13500, 15800, 14600, 16900, 17200, 19100, 16800, 15400, 14800, 18200],
  net_profit: [6100, 7200, 6300, 8800, 7500, 9900, 11200, 12100, 10700, 9900, 9100, 11500],
  cash_balance: [45000, 52200, 58500, 67300, 74800, 84700, 95900, 108000, 118700, 128600, 137700, 149200],
};

export const mockSalesTarget: SalesTarget = {
  business_name: "IBA Corp",
  current_revenue: 284500,
  target_revenue: 400000,
  percentage: 71.1,
};

export const mockTransactions: { transactions: Transaction[] } = {
  transactions: [
    { transaction_id: 10245, transaction_date: "2026-03-28", type: "Revenue", category: "Product Sales", amount: 4250.00, description: "Enterprise License — Q1 Renewal" },
    { transaction_id: 10244, transaction_date: "2026-03-27", type: "Expense", category: "Marketing", amount: 1800.00, description: "Google Ads Campaign — March" },
    { transaction_id: 10243, transaction_date: "2026-03-27", type: "Revenue", category: "Consulting", amount: 3500.00, description: "Strategy consultation — Acme Inc" },
    { transaction_id: 10242, transaction_date: "2026-03-26", type: "Expense", category: "Payroll", amount: 12500.00, description: "Bi-weekly payroll — Engineering" },
    { transaction_id: 10241, transaction_date: "2026-03-26", type: "Revenue", category: "Subscriptions", amount: 2100.00, description: "SaaS subscription — 14 new users" },
    { transaction_id: 10240, transaction_date: "2026-03-25", type: "Expense", category: "Software", amount: 890.00, description: "AWS hosting — March invoice" },
    { transaction_id: 10239, transaction_date: "2026-03-25", type: "Revenue", category: "Product Sales", amount: 6700.00, description: "Bulk order — RetailChain Ltd" },
    { transaction_id: 10238, transaction_date: "2026-03-24", type: "Expense", category: "Office", amount: 450.00, description: "Office supplies & equipment" },
    { transaction_id: 10237, transaction_date: "2026-03-24", type: "Revenue", category: "Consulting", amount: 2800.00, description: "Data analytics workshop" },
    { transaction_id: 10236, transaction_date: "2026-03-23", type: "Expense", category: "Travel", amount: 1200.00, description: "Client visit — Mumbai" },
  ],
};

export const mockCategories: { categories: string[] } = {
  categories: ["Product Sales", "Consulting", "Subscriptions", "Marketing", "Payroll", "Software", "Office", "Travel"],
};

export const mockRevenueVsExpense: RevenueVsExpense = {
  labels: ["Product Sales", "Consulting", "Subscriptions", "Marketing", "Payroll", "Software", "Office", "Travel"],
  revenue: [85400, 42300, 31200, 0, 0, 0, 0, 0],
  expenses: [0, 0, 0, 18600, 62500, 8900, 4500, 7200],
};

export const mockSalesTrend: SalesTrend = {
  labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
  revenue: [4200, 5100, 3800, 6400, 5900, 7200, 4800],
  expenses: [2800, 3200, 2500, 3900, 3400, 4100, 2900],
};

export const mockAlertsBySeverity: AlertsBySeverity = {
  labels: ["Critical", "Warning", "Info"],
  data: [1, 1, 1],
};

export const mockHealthScores: HealthScores = {
  businesses: ["IBA Corp"],
  scores: [
    {
      name: "IBA Corp",
      overall: 78,
      cash: 82,
      profitability: 75,
      growth: 68,
      cost_control: 84,
      risk: 71,
    },
  ],
};

export const mockTopProducts: TopProducts = {
  labels: ["Widget Pro", "DataSync", "CloudBase", "AI Toolkit", "SecureVault", "AnalytiX"],
  stock: [340, 210, 185, 420, 150, 290],
  margin: [4200, 5800, 3500, 6200, 4800, 5500],
  margin_amount: [4200, 5800, 3500, 6200, 4800, 5500],
  margin_pct: [42, 58, 35, 62, 48, 55],
};

export const mockEmployeeStats: EmployeeStats = {
  labels: ["Engineering", "Sales", "Marketing", "Support", "HR", "Finance"],
  counts: [45, 28, 16, 22, 8, 12],
  avg_salary: [95000, 72000, 68000, 55000, 65000, 78000],
};

export const mockForecast: Forecast = {
  historical: Array.from({ length: 60 }, (_, i) => ({
    date: new Date(Date.now() - (60 - i) * 86400000).toISOString().split("T")[0],
    actual: 5000 + Math.random() * 2000,
  })),
  forecast: Array.from({ length: 30 }, (_, i) => {
    const base = 6500 + i * 50;
    return {
      date: new Date(Date.now() + i * 86400000).toISOString().split("T")[0],
      predicted: base,
      lower_bound: base * 0.9,
      upper_bound: base * 1.1,
    };
  }),
  trend_direction: "up",
  trend_percent: 12.5,
  insight: "Your revenue is projected to grow by 12.5% over the next month, driven by strong seasonal trends in product sales. Consider increasing inventory for top-performing items.",
};
