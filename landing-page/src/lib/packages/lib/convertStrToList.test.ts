import { describe, expect, it } from "bun:test";
import { convertStrToList } from "./convertStrToList";

describe("convertStrToList", () => {
  it("should handle normal comma-separated input", () => {
    expect(convertStrToList("apple,banana,orange")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should trim whitespace around elements in comma-separated input", () => {
    expect(convertStrToList("  apple  , banana , orange   ")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should handle normal newline-separated input", () => {
    expect(convertStrToList("apple\nbanana\norange")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should trim whitespace around elements in newline-separated input", () => {
    expect(convertStrToList("  apple  \n banana \n orange   ")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should handle empty string input", () => {
    expect(convertStrToList("")).toEqual([""]);
  });

  it("should handle single-element string without delimiters", () => {
    expect(convertStrToList("apple")).toEqual(["apple"]);
  });

  it("should trim a single-element string", () => {
    expect(convertStrToList("   apple   ")).toEqual(["apple"]);
  });

  it("should filter out empty items from comma-separated input", () => {
    expect(convertStrToList("apple,,banana,,orange")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should filter out empty lines from newline-separated input", () => {
    expect(convertStrToList("apple\n\nbanana\n\norange")).toEqual([
      "apple",
      "banana",
      "orange",
    ]);
  });

  it("should handle strings with special characters", () => {
    expect(convertStrToList("@user1, #tag2, email@example.com")).toEqual([
      "@user1",
      "#tag2",
      "email@example.com",
    ]);
  });

  it("should prioritize newline separation over comma separation when both exist", () => {
    expect(convertStrToList("apple,banana\norange")).toEqual([
      "apple,banana",
      "orange",
    ]);
  });
});
