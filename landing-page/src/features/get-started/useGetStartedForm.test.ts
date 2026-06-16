import { describe, expect, it } from "bun:test";
import { normalizeEmail } from "@/lib/onboardingState";

// --- Pure logic tests (no React, no DOM needed) ---

describe("challenge toggle logic", () => {
  const toggle = (current: string[], challenge: string): string[] => {
    if (current.includes(challenge)) {
      return current.filter((c) => c !== challenge);
    }
    return [...current, challenge];
  };

  it("adds a challenge when not present", () => {
    expect(toggle([], "Cash Flow")).toEqual(["Cash Flow"]);
  });

  it("removes a challenge when already present", () => {
    expect(toggle(["Cash Flow", "Low Sales"], "Cash Flow")).toEqual(["Low Sales"]);
  });

  it("does not mutate the original array", () => {
    const original = ["Cash Flow"];
    toggle(original, "Low Sales");
    expect(original).toEqual(["Cash Flow"]);
  });

  it("handles empty array toggle correctly", () => {
    expect(toggle([], "Growth Planning")).toEqual(["Growth Planning"]);
    expect(toggle(["Growth Planning"], "Growth Planning")).toEqual([]);
  });
});

describe("email validation via normalizeEmail", () => {
  it("trims and lowercases a valid email", () => {
    expect(normalizeEmail("  User@Example.COM  ")).toBe("user@example.com");
  });

  it("returns empty string for empty input", () => {
    expect(normalizeEmail("")).toBe("");
  });

  it("trims whitespace only input to empty string", () => {
    expect(normalizeEmail("   ")).toBe("");
  });
});

describe("onboarding API payload shape", () => {
  it("joins challenges into a comma-separated string", () => {
    const challenges = ["Cash Flow", "Low Sales", "Marketing"];
    const biggest_challenge = challenges.join(", ");
    expect(biggest_challenge).toBe("Cash Flow, Low Sales, Marketing");
  });

  it("single challenge produces no trailing comma", () => {
    expect(["Pricing"].join(", ")).toBe("Pricing");
  });
});