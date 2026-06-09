/**
 * Unit tests for dashboard/src/lib/api.ts
 *
 * Strategy:
 *  - Spy on global.fetch to control HTTP responses without real network calls.
 *  - Mock ./publicUrls with a getter so AGENT_API_BASE is controllable per-test.
 *  - Mock ./mockData with a stable object for getForecast fallback tests.
 *  - Set global.window + global.localStorage to exercise the token path in
 *    getHeaders/getAuthHeaders (in Node, "localStorage" resolves to global.localStorage).
 *  - Provide lightweight DOM stubs for exportDashboardCsv.
 */

import {
  api,
  getAuthHeaders,
  listChatConversations,
  getChatConversation,
  upsertChatConversation,
  appendChatMessage,
  removeChatConversation,
} from "../api";
import type {
  DashboardSummary,
  FinancialOverview,
  RevenueVsExpense,
  SalesTrend,
  SalesTarget,
  Forecast,
  BusinessInfo,
  Categories,
  AlertsBySeverity,
  HealthScores,
  TopProducts,
  EmployeeStats,
} from "../api";
import type { ChatConversation, ChatMessage } from "../chatHistory";

// ---------------------------------------------------------------------------
// Module-level mocks
// ---------------------------------------------------------------------------

/**
 * Getter lets us change AGENT_API_BASE at runtime between tests.
 * ts-jest compiles named imports to property accesses on the require'd object,
 * so the getter is re-evaluated on every use of AGENT_API_BASE inside api.ts.
 */
let mockAgentApiBase = "";
jest.mock("../publicUrls", () => ({
  get AGENT_API_BASE() {
    return mockAgentApiBase;
  },
}));

/** Stable forecast fixture — returned by getForecast when the API fails. */
const MOCK_FORECAST: Forecast = {
  historical: [],
  forecast: [],
  trend_direction: "up",
  trend_percent: 5,
  insight: "mock insight",
};
jest.mock("../mockData", () => ({ mockForecast: MOCK_FORECAST }));

// ---------------------------------------------------------------------------
// Response factory helpers
// ---------------------------------------------------------------------------

function makeOk(body: unknown, status = 200): Partial<Response> {
  return {
    ok: true,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
    blob: async () => new Blob([JSON.stringify(body)]),
    headers: { get: () => "application/json" } as unknown as Headers,
  };
}

function makeJsonError(status: number, body: unknown): Partial<Response> {
  return {
    ok: false,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
    headers: { get: () => "application/json" } as unknown as Headers,
    statusText: `Error ${status}`,
  };
}

function makeTextError(
  status: number,
  text: string,
  statusText = `Error ${status}`
): Partial<Response> {
  return {
    ok: false,
    status,
    json: async () => { throw new Error("not json"); },
    text: async () => text,
    headers: { get: () => "text/plain" } as unknown as Headers,
    statusText,
  };
}

function makeBlobResponse(blob: Blob): Partial<Response> {
  return { ok: true, status: 200, blob: async () => blob };
}

// ---------------------------------------------------------------------------
// DOM stubs (for exportDashboardCsv)
// ---------------------------------------------------------------------------

interface DomStubs {
  mockAnchor: { href: string; download: string; click: jest.Mock; remove: jest.Mock };
  mockAppendChild: jest.Mock;
  mockCreateObjectURL: jest.Mock;
  mockRevokeObjectURL: jest.Mock;
}

function buildDomStubs(): DomStubs {
  const mockAnchor = { href: "", download: "", click: jest.fn(), remove: jest.fn() };
  const mockAppendChild = jest.fn();
  const mockCreateObjectURL = jest.fn().mockReturnValue("blob:fake-url");
  const mockRevokeObjectURL = jest.fn();

  // Make typeof window !== "undefined" inside api.ts
  // @ts-expect-error -- global not defined in the Node.js test environment
  global.window = {
    URL: { createObjectURL: mockCreateObjectURL, revokeObjectURL: mockRevokeObjectURL },
  };
  // In Node, bare "localStorage" resolves to global.localStorage (not window.localStorage)
  // @ts-expect-error -- global not defined in the Node.js test environment
  global.localStorage = { getItem: jest.fn().mockReturnValue(null) };
  // @ts-expect-error -- global not defined in the Node.js test environment
  global.document = {
    createElement: jest.fn().mockReturnValue(mockAnchor),
    body: { appendChild: mockAppendChild },
  };

  return { mockAnchor, mockAppendChild, mockCreateObjectURL, mockRevokeObjectURL };
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe("api.ts", () => {
  let fetchSpy: jest.SpyInstance;

  beforeEach(() => {
    fetchSpy = jest.spyOn(global, "fetch");
    mockAgentApiBase = "";
    // @ts-expect-error — keep Node env clean; DOM tests set it themselves
    delete global.window;
    // @ts-expect-error -- global not defined in the Node.js test environment
    delete global.localStorage;
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  // =========================================================================
  // getAuthHeaders()
  // =========================================================================

  describe("getAuthHeaders()", () => {
    afterEach(() => {
      // @ts-expect-error -- global not defined in the Node.js test environment
      delete global.window;
      // @ts-expect-error -- global not defined in the Node.js test environment
      delete global.localStorage;
    });

    it("returns an empty object when window is undefined (server / test env)", () => {
      expect(getAuthHeaders()).toEqual({});
    });

    it("returns an empty object when localStorage has no token", () => {
      // @ts-expect-error -- global not defined in the Node.js test environment
      global.window = {};
      // @ts-expect-error -- global not defined in the Node.js test environment
      global.localStorage = { getItem: jest.fn().mockReturnValue(null) };
      expect(getAuthHeaders()).toEqual({});
    });

    it("returns an Authorization header when a token is stored", () => {
      // @ts-expect-error -- global not defined in the Node.js test environment
      global.window = {};
      // @ts-expect-error -- global not defined in the Node.js test environment
      global.localStorage = { getItem: jest.fn().mockReturnValue("jwt-abc123") };
      expect(getAuthHeaders()).toEqual({ Authorization: "Bearer jwt-abc123" });
    });
  });

  // =========================================================================
  // api.getSummary()
  // =========================================================================

  describe("api.getSummary()", () => {
    const mockData: DashboardSummary = {
      total_revenue: 100_000,
      total_expenses: 50_000,
      net_profit: 50_000,
      total_transactions: 500,
      active_alerts: 3,
      revenue_change: 10,
      expenses_change: 5,
      net_profit_change: 15,
      transactions_change: 2,
    };

    it("fetches the correct URL with the given period", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getSummary("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/summary-sql?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON body on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getSummary("weekly")).toEqual(mockData);
    });

    it("throws an error that includes the HTTP status on failure", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 503,
        text: async () => "Service Unavailable",
      });
      await expect(api.getSummary("monthly")).rejects.toThrow(
        "Summary API failed (503)"
      );
    });

    it("includes the error body text in the thrown message", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 403,
        text: async () => "Forbidden — missing scope",
      });
      await expect(api.getSummary("monthly")).rejects.toThrow(
        "Forbidden — missing scope"
      );
    });
  });

  // =========================================================================
  // api.getFinancialOverview()
  // =========================================================================

  describe("api.getFinancialOverview()", () => {
    const mockData: FinancialOverview = {
      labels: ["Jan"],
      revenue: [100],
      expenses: [60],
      net_profit: [40],
      cash_balance: [200],
    };

    it("fetches without a query string when period is omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getFinancialOverview();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/financial-overview",
        expect.any(Object)
      );
    });

    it("appends ?period= when period is provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getFinancialOverview("quarterly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/financial-overview?period=quarterly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getFinancialOverview("monthly")).toEqual(mockData);
    });

    it("throws on non-ok response (message field in JSON body)", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeJsonError(500, { message: "Internal error" })
      );
      await expect(api.getFinancialOverview()).rejects.toThrow("Internal error");
    });
  });

  // =========================================================================
  // api.getRevenueVsExpense()
  // =========================================================================

  describe("api.getRevenueVsExpense()", () => {
    const mockData: RevenueVsExpense = {
      labels: ["Q1"],
      revenue: [5000],
      expenses: [3000],
    };

    it("fetches the correct URL with the period", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getRevenueVsExpense("yearly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/revenue-vs-expense?period=yearly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getRevenueVsExpense("monthly")).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(404, { message: "Not found" }));
      await expect(api.getRevenueVsExpense("monthly")).rejects.toThrow("Not found");
    });
  });

  // =========================================================================
  // api.getSalesTarget()
  // =========================================================================

  describe("api.getSalesTarget()", () => {
    const mockData: SalesTarget = {
      business_name: "Acme",
      current_revenue: 80_000,
      target_revenue: 100_000,
      percentage: 80,
    };

    it("fetches the correct URL", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getSalesTarget("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/sales-target?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getSalesTarget("weekly")).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeJsonError(401, { message: "Unauthorized" })
      );
      await expect(api.getSalesTarget("monthly")).rejects.toThrow("Unauthorized");
    });
  });

  // =========================================================================
  // api.getSalesTrend()
  // =========================================================================

  describe("api.getSalesTrend()", () => {
    const mockData: SalesTrend = {
      labels: ["Mon", "Tue"],
      revenue: [1000, 1200],
      expenses: [500, 600],
    };

    it("fetches the correct URL with the period", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getSalesTrend("weekly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/sales-trend?period=weekly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getSalesTrend("monthly")).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeJsonError(500, { message: "Server error" })
      );
      await expect(api.getSalesTrend("monthly")).rejects.toThrow("Server error");
    });
  });

  // =========================================================================
  // api.getForecast()
  // =========================================================================

  describe("api.getForecast()", () => {
    const realForecast: Forecast = {
      historical: [{ date: "2026-01-01", actual: 5000 }],
      forecast: [
        { date: "2026-02-01", predicted: 6000, lower_bound: 5500, upper_bound: 6500 },
      ],
      trend_direction: "up",
      trend_percent: 8,
      insight: "Strong growth.",
    };

    it("fetches the correct URL with the given period", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(realForecast));
      await api.getForecast("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/forecast?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON when the response is ok", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(realForecast));
      expect(await api.getForecast("monthly")).toEqual(realForecast);
    });

    it("returns mockForecast instead of throwing on a non-ok response", async () => {
      // getForecast has a unique silent-fallback behaviour — it never throws
      fetchSpy.mockResolvedValueOnce({ ok: false, status: 500 });
      const result = await api.getForecast("monthly");
      expect(result).toEqual(MOCK_FORECAST);
    });

    it("resolves with mockForecast even on 404 (does not propagate the error)", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: false, status: 404 });
      await expect(api.getForecast("monthly")).resolves.toEqual(MOCK_FORECAST);
    });
  });

  // =========================================================================
  // api.getRecentTransactions()
  // =========================================================================

  describe("api.getRecentTransactions()", () => {
    const mockBody = { transactions: [{ transaction_id: 1 }] };

    it("builds the URL with all provided params", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockBody));
      await api.getRecentTransactions({
        search: "rent",
        category: "Office",
        limit: 10,
        period: "monthly",
      });
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).toContain("search=rent");
      expect(url).toContain("category=Office");
      expect(url).toContain("limit=10");
      expect(url).toContain("period=monthly");
    });

    it("omits params that are not provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockBody));
      await api.getRecentTransactions({});
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).toContain("/api/dashboard/recent-transactions");
      expect(url).not.toContain("search=");
      expect(url).not.toContain("category=");
      expect(url).not.toContain("limit=");
      expect(url).not.toContain("period=");
    });

    it("silently omits limit=0 because `if (params.limit)` treats 0 as falsy", async () => {
      // This is a known edge case: limit:0 is a valid request but gets dropped.
      // A future fix could use params.limit !== undefined instead.
      fetchSpy.mockResolvedValueOnce(makeOk(mockBody));
      await api.getRecentTransactions({ limit: 0 });
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).not.toContain("limit=");
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockBody));
      expect(await api.getRecentTransactions({ period: "monthly" })).toEqual(mockBody);
    });

    it("throws with status code in the message on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => "Bad request",
      });
      await expect(api.getRecentTransactions({})).rejects.toThrow(
        "Recent transactions API failed (400)"
      );
    });

    it("includes the error body in the thrown message", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => "invalid period value",
      });
      await expect(api.getRecentTransactions({})).rejects.toThrow(
        "invalid period value"
      );
    });
  });

  // =========================================================================
  // api.getAlertsList()
  // =========================================================================

  describe("api.getAlertsList()", () => {
    it("fetches without a query string when period is omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk([]));
      await api.getAlertsList();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/alerts-list",
        expect.any(Object)
      );
    });

    it("appends ?period= when period is provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk([]));
      await api.getAlertsList("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/alerts-list?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      const alerts = [{ alert_id: 1, message: "Low cash" }];
      fetchSpy.mockResolvedValueOnce(makeOk(alerts));
      expect(await api.getAlertsList()).toEqual(alerts);
    });

    it("does NOT throw on non-ok status — res.ok is never checked (known bug)", async () => {
      // getAlertsList calls res.json() unconditionally.
      // It will resolve with whatever body the server sends, even on 4xx/5xx.
      const errorBody = { error: "Unauthorized" };
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => errorBody,
      });
      const result = await api.getAlertsList();
      expect(result).toEqual(errorBody);
    });
  });

  // =========================================================================
  // api.getBusinessInfo()
  // =========================================================================

  describe("api.getBusinessInfo()", () => {
    const mockData: BusinessInfo = {
      business_id: "biz-1",
      business_name: "Acme Corp",
      industry_type: "Tech",
      owner_name: "Alice",
    };

    it("fetches the correct endpoint", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getBusinessInfo();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/business-info",
        expect.any(Object)
      );
    });

    it("returns the parsed JSON on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getBusinessInfo()).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(403, { message: "Forbidden" }));
      await expect(api.getBusinessInfo()).rejects.toThrow("Forbidden");
    });
  });

  // =========================================================================
  // api.getCategories()
  // =========================================================================

  describe("api.getCategories()", () => {
    it("fetches the correct endpoint", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ categories: [] }));
      await api.getCategories();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/categories",
        expect.any(Object)
      );
    });

    it("returns the categories payload on success", async () => {
      const payload: Categories = { categories: ["Sales", "Support"] };
      fetchSpy.mockResolvedValueOnce(makeOk(payload));
      expect(await api.getCategories()).toEqual(payload);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(500, { message: "DB error" }));
      await expect(api.getCategories()).rejects.toThrow("DB error");
    });
  });

  // =========================================================================
  // api.getAlertsBySeverity()
  // =========================================================================

  describe("api.getAlertsBySeverity()", () => {
    const mockData: AlertsBySeverity = { labels: ["Critical", "Warning"], data: [2, 5] };

    it("fetches without period when omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getAlertsBySeverity();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/alerts-by-severity",
        expect.any(Object)
      );
    });

    it("appends ?period= when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getAlertsBySeverity("weekly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/alerts-by-severity?period=weekly",
        expect.any(Object)
      );
    });

    it("returns the parsed payload on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getAlertsBySeverity()).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(500, { message: "Internal" }));
      await expect(api.getAlertsBySeverity()).rejects.toThrow("Internal");
    });
  });

  // =========================================================================
  // api.getHealthScores()
  // =========================================================================

  describe("api.getHealthScores()", () => {
    const mockData: HealthScores = {
      businesses: ["Acme"],
      scores: [
        {
          name: "Acme",
          overall: 90,
          cash: 85,
          profitability: 88,
          growth: 80,
          cost_control: 92,
          risk: 75,
        },
      ],
    };

    it("fetches without period when omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getHealthScores();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/health-scores",
        expect.any(Object)
      );
    });

    it("appends ?period= when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getHealthScores("quarterly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/health-scores?period=quarterly",
        expect.any(Object)
      );
    });

    it("returns the parsed payload on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getHealthScores()).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(401, { message: "Unauthorized" }));
      await expect(api.getHealthScores()).rejects.toThrow("Unauthorized");
    });
  });

  // =========================================================================
  // api.getTopProducts()
  // =========================================================================

  describe("api.getTopProducts()", () => {
    const mockData: TopProducts = { labels: ["Widget"], stock: [100], margin: [40] };

    it("fetches without period when omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getTopProducts();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/top-products",
        expect.any(Object)
      );
    });

    it("appends ?period= when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getTopProducts("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/top-products?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed payload on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getTopProducts()).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(503, { message: "Unavailable" }));
      await expect(api.getTopProducts()).rejects.toThrow("Unavailable");
    });
  });

  // =========================================================================
  // api.getEmployeeStats()
  // =========================================================================

  describe("api.getEmployeeStats()", () => {
    const mockData: EmployeeStats = {
      labels: ["Engineering"],
      counts: [30],
      avg_salary: [90_000],
    };

    it("fetches without period when omitted", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getEmployeeStats();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/employee-stats",
        expect.any(Object)
      );
    });

    it("appends ?period= when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      await api.getEmployeeStats("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/employee-stats?period=monthly",
        expect.any(Object)
      );
    });

    it("returns the parsed payload on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk(mockData));
      expect(await api.getEmployeeStats()).toEqual(mockData);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeJsonError(401, { message: "Unauthorized" }));
      await expect(api.getEmployeeStats()).rejects.toThrow("Unauthorized");
    });
  });

  // =========================================================================
  // safeFetchJson — shared error-handling logic (tested via getBusinessInfo)
  // =========================================================================

  describe("safeFetchJson() error-handling (exercised via api.getBusinessInfo)", () => {
    it("uses the message field from a JSON error body", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeJsonError(422, { message: "Validation failed" })
      );
      await expect(api.getBusinessInfo()).rejects.toThrow("Validation failed");
    });

    it("stringifies the full JSON body when there is no message field", async () => {
      const errorBody = { code: "ERR_UNKNOWN", detail: "oops" };
      fetchSpy.mockResolvedValueOnce(makeJsonError(400, errorBody));
      await expect(api.getBusinessInfo()).rejects.toThrow(
        JSON.stringify(errorBody)
      );
    });

    it("uses the plain-text body when Content-Type is not JSON", async () => {
      fetchSpy.mockResolvedValueOnce(makeTextError(502, "Bad Gateway"));
      await expect(api.getBusinessInfo()).rejects.toThrow("Bad Gateway");
    });

    it("falls back to `HTTP <status>` when both json() and text() throw", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 503,
        headers: { get: () => "application/json" } as unknown as Headers,
        json: async () => { throw new Error("parse error"); },
        text: async () => { throw new Error("text error"); },
      });
      await expect(api.getBusinessInfo()).rejects.toThrow("HTTP 503");
    });
  });

  // =========================================================================
  // api.exportDashboardCsv()
  // =========================================================================

  describe("api.exportDashboardCsv()", () => {
    let stubs: DomStubs;

    beforeEach(() => {
      stubs = buildDomStubs();
    });

    afterEach(() => {
      // @ts-expect-error -- global not defined in the Node.js test environment
      delete global.window;
      // @ts-expect-error -- global not defined in the Node.js test environment
      delete global.document;
      // @ts-expect-error -- global not defined in the Node.js test environment
      delete global.localStorage;
    });

    it("fetches the export endpoint with the correct period", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeBlobResponse(new Blob(["col1,col2"], { type: "text/csv" }))
      );
      await api.exportDashboardCsv("monthly");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/dashboard/export-csv?period=monthly",
        expect.any(Object)
      );
    });

    it("creates an object URL from the response blob", async () => {
      const blob = new Blob(["data"], { type: "text/csv" });
      fetchSpy.mockResolvedValueOnce(makeBlobResponse(blob));
      await api.exportDashboardCsv("weekly");
      expect(stubs.mockCreateObjectURL).toHaveBeenCalledWith(blob);
    });

    it("triggers a click on the temporary anchor and removes it", async () => {
      fetchSpy.mockResolvedValueOnce(
        makeBlobResponse(new Blob(["data"]))
      );
      await api.exportDashboardCsv("monthly");
      expect(stubs.mockAnchor.click).toHaveBeenCalled();
      expect(stubs.mockAnchor.remove).toHaveBeenCalled();
    });

    it("revokes the object URL after the download is triggered", async () => {
      fetchSpy.mockResolvedValueOnce(makeBlobResponse(new Blob(["data"])));
      await api.exportDashboardCsv("monthly");
      expect(stubs.mockRevokeObjectURL).toHaveBeenCalledWith("blob:fake-url");
    });

    it("sets a download filename containing the period and an ISO date", async () => {
      fetchSpy.mockResolvedValueOnce(makeBlobResponse(new Blob(["data"])));
      await api.exportDashboardCsv("quarterly");
      expect(stubs.mockAnchor.download).toMatch(
        /^profitpilot_export_quarterly_\d{4}-\d{2}-\d{2}\.csv$/
      );
    });

    it("throws 'Export failed' when the response is not ok", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: false, status: 500 });
      await expect(api.exportDashboardCsv("monthly")).rejects.toThrow(
        "Export failed"
      );
    });
  });

  // =========================================================================
  // listChatConversations()
  // =========================================================================

  describe("listChatConversations()", () => {
    const conversations: ChatConversation[] = [
      { id: "c1", title: "Hello", messages: [], createdAt: 1000, updatedAt: 1000 },
    ];

    it("fetches /api/chat/conversations with cache: no-store", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversations }));
      await listChatConversations();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations",
        expect.objectContaining({ cache: "no-store" })
      );
    });

    it("returns the conversations array on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversations }));
      expect(await listChatConversations()).toEqual(conversations);
    });

    it("returns an empty array when the conversations key is absent", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({}));
      expect(await listChatConversations()).toEqual([]);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeTextError(401, "Unauthorized"));
      await expect(listChatConversations()).rejects.toThrow("Unauthorized");
    });

    it("prefixes the URL with AGENT_API_BASE when it is set", async () => {
      mockAgentApiBase = "http://chat-api:8080";
      fetchSpy.mockResolvedValueOnce(makeOk({ conversations: [] }));
      await listChatConversations();
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://chat-api:8080/api/chat/conversations",
        expect.any(Object)
      );
      mockAgentApiBase = "";
    });

    it("uses a bare path when AGENT_API_BASE is empty", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversations: [] }));
      await listChatConversations();
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations",
        expect.any(Object)
      );
    });
  });

  // =========================================================================
  // getChatConversation()
  // =========================================================================

  describe("getChatConversation()", () => {
    const conversation: ChatConversation = {
      id: "conv-42",
      title: "Revenue Q1",
      messages: [],
      createdAt: 2000,
      updatedAt: 3000,
    };

    it("fetches the correct URL for the given conversationId", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await getChatConversation("conv-42");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations/conv-42",
        expect.any(Object)
      );
    });

    it("URL-encodes special characters in the conversationId", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await getChatConversation("conv 42/test");
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).toContain("conv%2042%2Ftest");
    });

    it("returns the conversation object on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      expect(await getChatConversation("conv-42")).toEqual(conversation);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeTextError(404, "Not found"));
      await expect(getChatConversation("missing")).rejects.toThrow("Not found");
    });

    it("falls back to statusText when text() throws", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => { throw new Error("body unavailable"); },
        statusText: "Internal Server Error",
      });
      await expect(getChatConversation("conv-1")).rejects.toThrow(
        "Internal Server Error"
      );
    });
  });

  // =========================================================================
  // upsertChatConversation()
  // =========================================================================

  describe("upsertChatConversation()", () => {
    const conversation: ChatConversation = {
      id: "conv-5",
      title: "Expenses",
      messages: [{ role: "user", content: "Hi", timestamp: 100, intent: null }],
      createdAt: 100,
      updatedAt: 200,
    };

    it("sends a PUT request to the correct URL", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await upsertChatConversation(conversation);
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations/conv-5",
        expect.objectContaining({ method: "PUT" })
      );
    });

    it("sends title, messages, createdAt, and updatedAt in the JSON body", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await upsertChatConversation(conversation);
      const body = JSON.parse(
        (fetchSpy.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body).toMatchObject({
        title: "Expenses",
        messages: conversation.messages,
        createdAt: 100,
        updatedAt: 200,
      });
    });

    it("returns the upserted conversation on success", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      expect(await upsertChatConversation(conversation)).toEqual(conversation);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeTextError(500, "Server error"));
      await expect(upsertChatConversation(conversation)).rejects.toThrow(
        "Server error"
      );
    });
  });

  // =========================================================================
  // appendChatMessage()
  // =========================================================================

  describe("appendChatMessage()", () => {
    const conversation: ChatConversation = {
      id: "conv-7",
      title: "Q&A",
      messages: [],
      createdAt: 500,
      updatedAt: 600,
    };
    const message: ChatMessage = {
      role: "user",
      content: "What is profit?",
      timestamp: 700,
      intent: null,
    };

    it("sends a POST to the messages sub-path", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await appendChatMessage("conv-7", "Q&A", message);
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations/conv-7/messages",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("uses message.timestamp as updatedAt when no metadata is provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await appendChatMessage("conv-7", "Q&A", message);
      const body = JSON.parse(
        (fetchSpy.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body.updatedAt).toBe(700);
    });

    it("uses metadata.updatedAt when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await appendChatMessage("conv-7", "Q&A", message, { updatedAt: 9999 });
      const body = JSON.parse(
        (fetchSpy.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body.updatedAt).toBe(9999);
    });

    it("sends metadata.createdAt in the body when provided", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await appendChatMessage("conv-7", "Q&A", message, { createdAt: 1111 });
      const body = JSON.parse(
        (fetchSpy.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body.createdAt).toBe(1111);
    });

    it("includes the full message object in the body", async () => {
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation }));
      await appendChatMessage("conv-7", "Q&A", message);
      const body = JSON.parse(
        (fetchSpy.mock.calls[0][1] as RequestInit).body as string
      );
      expect(body.message).toEqual(message);
    });

    it("returns the updated conversation on success", async () => {
      const updated = { ...conversation, messages: [message] };
      fetchSpy.mockResolvedValueOnce(makeOk({ conversation: updated }));
      expect(await appendChatMessage("conv-7", "Q&A", message)).toEqual(updated);
    });

    it("throws on non-ok response", async () => {
      fetchSpy.mockResolvedValueOnce(makeTextError(400, "Bad request"));
      await expect(appendChatMessage("conv-7", "Q&A", message)).rejects.toThrow(
        "Bad request"
      );
    });
  });

  // =========================================================================
  // removeChatConversation()
  // =========================================================================

  describe("removeChatConversation()", () => {
    it("sends a DELETE request to the correct URL", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: true, status: 204 });
      await removeChatConversation("conv-9");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/chat/conversations/conv-9",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("resolves without a value on 204 No Content", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: true, status: 204 });
      await expect(removeChatConversation("conv-9")).resolves.toBeUndefined();
    });

    it("resolves without throwing on 404 (idempotent delete)", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 404,
        text: async () => "Not Found",
        statusText: "Not Found",
      });
      await expect(removeChatConversation("conv-9")).resolves.toBeUndefined();
    });

    it("throws on non-ok, non-404 responses", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => "Server error",
        statusText: "Internal Server Error",
      });
      await expect(removeChatConversation("conv-9")).rejects.toThrow("Server error");
    });

    it("falls back to statusText when text() throws", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 503,
        text: async () => { throw new Error("body unavailable"); },
        statusText: "Service Unavailable",
      });
      await expect(removeChatConversation("conv-9")).rejects.toThrow(
        "Service Unavailable"
      );
    });

    it("uses the fallback message when both text and statusText are empty", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 502,
        text: async () => "",
        statusText: "",
      });
      await expect(removeChatConversation("conv-9")).rejects.toThrow(
        "Delete failed with status 502"
      );
    });

    it("URL-encodes special characters in the conversationId", async () => {
      fetchSpy.mockResolvedValueOnce({ ok: true, status: 200 });
      await removeChatConversation("my conv/1");
      const url = fetchSpy.mock.calls[0][0] as string;
      expect(url).toContain("my%20conv%2F1");
    });
  });
});
