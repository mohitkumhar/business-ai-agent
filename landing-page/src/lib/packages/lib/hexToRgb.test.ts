import { describe, expect, it } from "bun:test";
import { hexToRgb, isLight } from "./hexToRgb";

describe("hexToRgb", () => {
  it("should parse full hex color values", () => {
    expect(hexToRgb("#00ff7f")).toEqual([0, 255, 127]);
    expect(hexToRgb("00ff7f")).toEqual([0, 255, 127]);
    expect(hexToRgb("FF00FF")).toEqual([255, 0, 255]);
  });

  it("should parse shorthand hex color values", () => {
    expect(hexToRgb("#0f7")).toEqual([0, 255, 119]);
    expect(hexToRgb("0f7")).toEqual([0, 255, 119]);
    expect(hexToRgb("F0A")).toEqual([255, 0, 170]);
  });

  it("should return black for invalid inputs", () => {
    expect(hexToRgb("#xyz")).toEqual([0, 0, 0]);
    expect(hexToRgb("12345")).toEqual([0, 0, 0]);
    expect(hexToRgb("#ff")).toEqual([0, 0, 0]);
    expect(hexToRgb("")).toEqual([0, 0, 0]);
  });
});

describe("isLight", () => {
  it("should identify light colors correctly", () => {
    expect(isLight("#ffffff")).toBe(true);
    expect(isLight("fff")).toBe(true);
    expect(isLight("#eeeeee")).toBe(true);
  });

  it("should identify dark colors correctly", () => {
    expect(isLight("#000000")).toBe(false);
    expect(isLight("000")).toBe(false);
    expect(isLight("#101010")).toBe(false);
  });

  it("should treat invalid colors as dark", () => {
    expect(isLight("#zzz")).toBe(false);
    expect(isLight("invalid")).toBe(false);
  });
});
