/**
 * __tests__/apiClient.test.js
 * Unit tests for API client functions
 */

import { afterEach, beforeEach, describe, it, mock } from "node:test";
import assert from "node:assert/strict";
import {
  fetchJSON,
  fetchKPISummary,
  fetchRevenueExpense,
  fetchTransactionsByCategory,
  fetchSalesTrend,
  fetchAlertsBySeverity,
  fetchFinancialOverview,
  fetchTopProducts,
  fetchHealthScores,
  fetchEmployeeStats,
} from "../apiClient.js";

describe("apiClient", () => {
  beforeEach(() => {
    globalThis.fetch = mock.fn();
    mock.method(console, "error", () => {});
  });

  afterEach(() => {
    mock.restoreAll();
    delete globalThis.fetch;
  });

  describe("fetchJSON function", () => {
    it("should fetch and parse JSON successfully", async () => {
      const mockData = { success: true, value: 123 };
      globalThis.fetch = mock.fn(async () => ({
        ok: true,
        json: async () => mockData,
      }));

      const result = await fetchJSON("/api/test");

      assert.deepEqual(globalThis.fetch.mock.calls[0].arguments, ["/api/test"]);
      assert.deepEqual(result, mockData);
    });

    it("should return null on fetch error", async () => {
      globalThis.fetch = mock.fn(async () => {
        throw new Error("Network error");
      });

      const result = await fetchJSON("/api/test");

      assert.equal(result, null);
      assert.equal(console.error.mock.calls.length, 1);
    });

    it("should return null on non-200 status", async () => {
      globalThis.fetch = mock.fn(async () => ({
        ok: false,
        status: 404,
      }));

      const result = await fetchJSON("/api/test");

      assert.equal(result, null);
      assert.equal(console.error.mock.calls.length, 1);
    });

    it("should return null on invalid JSON response", async () => {
      globalThis.fetch = mock.fn(async () => ({
        ok: true,
        json: async () => {
          throw new Error("Invalid JSON");
        },
      }));

      const result = await fetchJSON("/api/test");

      assert.equal(result, null);
      assert.equal(console.error.mock.calls.length, 1);
    });
  });

  describe("Specific API endpoint functions", () => {
    it("should call fetchJSON with correct endpoints", async () => {
      globalThis.fetch = mock.fn(async () => ({
        ok: true,
        json: async () => ({}),
      }));

      await fetchKPISummary();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/summary",
      ]);

      await fetchRevenueExpense();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/revenue-vs-expense",
      ]);

      await fetchTransactionsByCategory();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/transactions-by-category",
      ]);

      await fetchSalesTrend();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/sales-trend",
      ]);

      await fetchAlertsBySeverity();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/alerts-by-severity",
      ]);

      await fetchFinancialOverview();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/financial-overview",
      ]);

      await fetchTopProducts();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/top-products",
      ]);

      await fetchHealthScores();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/health-scores",
      ]);

      await fetchEmployeeStats();
      assert.deepEqual(globalThis.fetch.mock.calls.at(-1).arguments, [
        "/api/dashboard/employee-stats",
      ]);
    });

    it("should return null when endpoints fail", async () => {
      globalThis.fetch = mock.fn(async () => {
        throw new Error("Network error");
      });

      const results = await Promise.all([
        fetchKPISummary(),
        fetchRevenueExpense(),
        fetchTransactionsByCategory(),
        fetchSalesTrend(),
        fetchAlertsBySeverity(),
        fetchFinancialOverview(),
        fetchTopProducts(),
        fetchHealthScores(),
        fetchEmployeeStats(),
      ]);

      results.forEach((result) => {
        assert.equal(result, null);
      });
    });
  });
});
