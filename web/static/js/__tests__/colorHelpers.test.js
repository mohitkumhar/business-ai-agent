/**
 * __tests__/colorHelpers.test.js
 * Unit tests for color utilities
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  COLORS,
  PALETTE,
  rgba,
  SEVERITY_COLORS,
  STATUS_COLORS,
  getSeverityColor,
  getStatusColor,
} from "../colorHelpers.js";

describe("colorHelpers", () => {
  describe("COLORS constant", () => {
    it("should contain all color definitions", () => {
      assert.ok(COLORS);
      assert.equal(COLORS.blue, "#5b8af5");
      assert.equal(COLORS.green, "#4ecb71");
      assert.equal(COLORS.red, "#f55b6a");
      assert.equal(COLORS.orange, "#f5a623");
      assert.equal(COLORS.purple, "#a855f7");
      assert.equal(COLORS.cyan, "#22d3ee");
      assert.equal(COLORS.pink, "#ec4899");
      assert.equal(COLORS.lime, "#84cc16");
    });
  });

  describe("PALETTE constant", () => {
    it("should contain all colors in order", () => {
      assert.equal(PALETTE.length, 8);
      assert.equal(PALETTE[0], "#5b8af5");
      assert.equal(PALETTE[1], "#4ecb71");
    });
  });

  describe("rgba function", () => {
    it("should convert hex to RGBA format correctly", () => {
      const result = rgba("#5b8af5", 0.7);
      assert.equal(result, "rgba(91,138,245,0.7)");
    });

    it("should handle different alpha values", () => {
      const result1 = rgba("#4ecb71", 0.5);
      assert.equal(result1, "rgba(78,203,113,0.5)");

      const result2 = rgba("#f55b6a", 0.1);
      assert.equal(result2, "rgba(245,91,106,0.1)");
    });

    it("should handle alpha value of 0 and 1", () => {
      assert.equal(rgba("#5b8af5", 0), "rgba(91,138,245,0)");
      assert.equal(rgba("#5b8af5", 1), "rgba(91,138,245,1)");
    });
  });

  describe("SEVERITY_COLORS mapping", () => {
    it("should map severity levels to colors", () => {
      assert.equal(SEVERITY_COLORS.Low, COLORS.green);
      assert.equal(SEVERITY_COLORS.Medium, COLORS.orange);
      assert.equal(SEVERITY_COLORS.High, COLORS.red);
    });
  });

  describe("STATUS_COLORS mapping", () => {
    it("should map status to colors", () => {
      assert.equal(STATUS_COLORS.Active, COLORS.green);
      assert.equal(STATUS_COLORS.Left, COLORS.red);
    });
  });

  describe("getSeverityColor function", () => {
    it("should return correct color for known severity levels", () => {
      assert.equal(getSeverityColor("Low"), COLORS.green);
      assert.equal(getSeverityColor("Medium"), COLORS.orange);
      assert.equal(getSeverityColor("High"), COLORS.red);
    });

    it("should return purple for unknown severity levels", () => {
      assert.equal(getSeverityColor("Unknown"), COLORS.purple);
      assert.equal(getSeverityColor("Critical"), COLORS.purple);
    });
  });

  describe("getStatusColor function", () => {
    it("should return correct color for known statuses", () => {
      assert.equal(getStatusColor("Active"), COLORS.green);
      assert.equal(getStatusColor("Left"), COLORS.red);
    });

    it("should return purple for unknown statuses", () => {
      assert.equal(getStatusColor("Unknown"), COLORS.purple);
      assert.equal(getStatusColor("Pending"), COLORS.purple);
    });
  });
});
