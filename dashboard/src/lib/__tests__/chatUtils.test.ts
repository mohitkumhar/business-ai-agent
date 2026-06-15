/**
 * Regression tests for dashboard/src/lib/chatUtils.ts
 *
 * Strategy:
 *  - Pure functions, no mocks needed.
 *  - Cover boundary values (zero, negatives, large numbers) and the
 *    band thresholds used for INR currency formatting and severity labels.
 */
import {
  friendlyNodeName,
  relativeTime,
  formatCurrency,
  formatNumber,
  formatPct,
  severityBadgeLabel,
} from "../chatUtils";

describe("friendlyNodeName", () => {
  it("replaces underscores with spaces and title-cases words", () => {
    expect(friendlyNodeName("total_revenue")).toBe("Total Revenue");
    expect(friendlyNodeName("net_profit_change")).toBe("Net Profit Change");
  });

  it("handles single words without underscores", () => {
    expect(friendlyNodeName("alerts")).toBe("Alerts");
  });
});

describe("relativeTime", () => {
  it("returns 'Just now' for timestamps under a minute old", () => {
    expect(relativeTime(Date.now())).toBe("Just now");
  });

  it("returns minutes for timestamps under an hour old", () => {
    const fiveMinAgo = Date.now() - 5 * 60 * 1000;
    expect(relativeTime(fiveMinAgo)).toBe("5m ago");
  });

  it("returns hours for timestamps under a day old", () => {
    const twoHoursAgo = Date.now() - 2 * 60 * 60 * 1000;
    expect(relativeTime(twoHoursAgo)).toBe("2h ago");
  });

  it("returns days for timestamps a day or more old", () => {
    const threeDaysAgo = Date.now() - 3 * 24 * 60 * 60 * 1000;
    expect(relativeTime(threeDaysAgo)).toBe("3d ago");
  });
});

describe("formatCurrency", () => {
  it("formats crore-scale values with the Cr suffix", () => {
    expect(formatCurrency(15000000)).toBe("₹1.50 Cr");
  });

  it("formats lakh-scale values with the L suffix", () => {
    expect(formatCurrency(250000)).toBe("₹2.50 L");
  });

  it("formats thousand-scale values with the K suffix", () => {
    expect(formatCurrency(5000)).toBe("₹5.0 K");
  });

  it("formats sub-thousand values with locale grouping", () => {
    expect(formatCurrency(500)).toBe("₹500");
  });

  it("formats zero correctly", () => {
    expect(formatCurrency(0)).toBe("₹0");
  });

  it("formats negative values with a leading minus sign", () => {
    expect(formatCurrency(-250000)).toBe("-₹2.50 L");
  });
});

describe("formatNumber", () => {
  it("formats millions with the M suffix", () => {
    expect(formatNumber(2_500_000)).toBe("2.5M");
  });

  it("formats thousands with the K suffix", () => {
    expect(formatNumber(3_200)).toBe("3.2K");
  });

  it("formats sub-thousand values with locale grouping", () => {
    expect(formatNumber(42)).toBe("42");
  });

  it("formats zero correctly", () => {
    expect(formatNumber(0)).toBe("0");
  });
});

describe("formatPct", () => {
  it("returns an em dash for null or undefined", () => {
    expect(formatPct(null)).toBe("—");
    expect(formatPct(undefined)).toBe("—");
  });

  it("returns an em dash for NaN", () => {
    expect(formatPct(NaN)).toBe("—");
  });

  it("prefixes positive percentages with a plus sign", () => {
    expect(formatPct(4.5)).toBe("+4.5%");
  });

  it("does not prefix negative percentages", () => {
    expect(formatPct(-4.5)).toBe("-4.5%");
  });

  it("does not prefix zero", () => {
    expect(formatPct(0)).toBe("0.0%");
  });
});

describe("severityBadgeLabel", () => {
  it("returns 'Active' for null or undefined", () => {
    expect(severityBadgeLabel(null)).toBe("Active");
    expect(severityBadgeLabel(undefined)).toBe("Active");
  });

  it("maps 'High' to 'Critical'", () => {
    expect(severityBadgeLabel("High")).toBe("Critical");
  });

  it("returns 'Medium' and 'Low' unchanged", () => {
    expect(severityBadgeLabel("Medium")).toBe("Medium");
    expect(severityBadgeLabel("Low")).toBe("Low");
  });

  it("returns unrecognized severity values unchanged", () => {
    expect(severityBadgeLabel("Unknown")).toBe("Unknown");
  });
});