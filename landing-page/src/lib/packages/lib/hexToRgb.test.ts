import { describe, expect, it } from "bun:test";
import { hexToRgb, isLight } from "./hexToRgb";

describe("hexToRgb", () => {
  it("converts six-digit hex colors with a leading hash", () => {
    expect(hexToRgb("#1a2b3c")).toEqual([26, 43, 60]);
  });

  it("converts six-digit hex colors without a leading hash", () => {
    expect(hexToRgb("ff8800")).toEqual([255, 136, 0]);
  });

  it("expands three-digit shorthand hex colors", () => {
    expect(hexToRgb("#abc")).toEqual([170, 187, 204]);
  });

  it("handles uppercase hex values", () => {
    expect(hexToRgb("#FAEBD7")).toEqual([250, 235, 215]);
  });

  it("falls back to black for invalid hex input", () => {
    expect(hexToRgb("not-a-color")).toEqual([0, 0, 0]);
  });
});

describe("isLight", () => {
  it("detects light colors", () => {
    expect(isLight("#ffffff")).toBe(true);
  });

  it("detects dark colors", () => {
    expect(isLight("#111111")).toBe(false);
  });
});
