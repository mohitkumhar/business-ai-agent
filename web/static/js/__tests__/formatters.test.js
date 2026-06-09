/**
 * __tests__/formatters.test.js
 * Unit tests for data formatting utilities
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { currency, formatNumber, formatPercent } from "../formatters.js";

describe("formatters", () => {
  describe("currency function", () => {
    it("should format numbers as USD currency", () => {
      assert.equal(currency(1234567), "$1,234,567");
      assert.equal(currency(0), "$0");
      assert.equal(currency(99), "$99");
    });

    it("should handle negative numbers", () => {
      assert.equal(currency(-1000), "$-1,000");
      assert.equal(currency(-99999), "$-99,999");
    });

    it("should handle decimal numbers (truncate decimals)", () => {
      assert.equal(currency(1234.56), "$1,235");
      assert.equal(currency(999.99), "$1,000");
    });

    it("should handle string numbers", () => {
      assert.equal(currency("5000"), "$5,000");
      assert.equal(currency("1000000"), "$1,000,000");
    });

    it("should handle very large numbers", () => {
      assert.equal(currency(1000000000), "$1,000,000,000");
    });
  });

  describe("formatNumber function", () => {
    it("should format numbers with comma separators", () => {
      assert.equal(formatNumber(1234567), "1,234,567");
      assert.equal(formatNumber(1000), "1,000");
      assert.equal(formatNumber(99), "99");
    });

    it("should handle negative numbers", () => {
      assert.equal(formatNumber(-1000), "-1,000");
      assert.equal(formatNumber(-5000000), "-5,000,000");
    });

    it("should handle string numbers", () => {
      assert.equal(formatNumber("2000"), "2,000");
      assert.equal(formatNumber("500000"), "500,000");
    });

    it("should handle decimal numbers", () => {
      assert.equal(formatNumber(1000.5), "1,000.5");
      assert.equal(formatNumber(5000.99), "5,000.99");
    });
  });

  describe("formatPercent function", () => {
    it("should format numbers as percentages with default 2 decimals", () => {
      assert.equal(formatPercent(50), "50.00%");
      assert.equal(formatPercent(75.5), "75.50%");
      assert.equal(formatPercent(0), "0.00%");
    });

    it("should respect custom decimal places", () => {
      assert.equal(formatPercent(33.333, 0), "33%");
      assert.equal(formatPercent(33.333, 1), "33.3%");
      assert.equal(formatPercent(33.333, 3), "33.333%");
    });

    it("should handle large percentages", () => {
      assert.equal(formatPercent(100), "100.00%");
      assert.equal(formatPercent(999.99), "999.99%");
    });

    it("should handle negative percentages", () => {
      assert.equal(formatPercent(-50), "-50.00%");
      assert.equal(formatPercent(-25.5), "-25.50%");
    });

    it("should handle very small numbers", () => {
      assert.equal(formatPercent(0.001), "0.00%");
      assert.equal(formatPercent(0.1, 3), "0.100%");
    });
  });
});
