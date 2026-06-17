import { describe, expect, it } from "bun:test";
import { convertStrToList } from "./convertStrToList";

describe("convertStrToList", () => {
  // ── Normal behaviour ──────────────────────────────────────────────────────

  it("should return a single-element array for a plain string with no delimiter", () => {
    expect(convertStrToList("hello")).toEqual(["hello"]);
  });

  it("should split a comma-separated string into trimmed items", () => {
    expect(convertStrToList("apple,banana,cherry")).toEqual([
      "apple",
      "banana",
      "cherry",
    ]);
  });

  it("should split a newline-separated string into trimmed items", () => {
    expect(convertStrToList("apple\nbanana\ncherry")).toEqual([
      "apple",
      "banana",
      "cherry",
    ]);
  });

  it("should prefer newline splitting over comma splitting when both delimiters are present", () => {
    expect(convertStrToList("a,b\nc,d")).toEqual(["a,b", "c,d"]);
  });

  // ── Whitespace handling ───────────────────────────────────────────────────

  it("should trim leading and trailing whitespace from each item (comma)", () => {
    expect(convertStrToList("  foo  ,  bar  ,  baz  ")).toEqual([
      "foo",
      "bar",
      "baz",
    ]);
  });

  it("should trim leading and trailing whitespace from each item (newline)", () => {
    expect(convertStrToList("  foo  \n  bar  \n  baz  ")).toEqual([
      "foo",
      "bar",
      "baz",
    ]);
  });

  it("should trim a single-item string", () => {
    expect(convertStrToList("  hello  ")).toEqual(["hello"]);
  });

  // ── Empty / blank values ──────────────────────────────────────────────────

  it("should filter out empty strings produced by trailing commas", () => {
    expect(convertStrToList("a,b,c,")).toEqual(["a", "b", "c"]);
  });

  it("should filter out empty strings produced by trailing newlines", () => {
    expect(convertStrToList("a\nb\nc\n")).toEqual(["a", "b", "c"]);
  });

  it("should filter out blank lines between items", () => {
    expect(convertStrToList("a\n\nb\n\nc")).toEqual(["a", "b", "c"]);
  });

  it("should return a single-element array for an empty string", () => {
    expect(convertStrToList("")).toEqual([""]);
  });

  it("should return [''] for a whitespace-only string", () => {
    expect(convertStrToList("   ")).toEqual([""]);
  });

  // ── Single-item edge cases ────────────────────────────────────────────────

  it("should return a single-element array for a one-character string", () => {
    expect(convertStrToList("x")).toEqual(["x"]);
  });

  it("should return a single-element array for a two-character string with no delimiter", () => {
    expect(convertStrToList("ab")).toEqual(["ab"]);
  });

  // ── Special characters ───────────────────────────────────────────────────

  it("should handle strings with special characters as a single item", () => {
    expect(convertStrToList("hello@world!")).toEqual(["hello@world!"]);
  });

  it("should split correctly when items contain special characters", () => {
    expect(convertStrToList("hello@world,foo#bar")).toEqual([
      "hello@world",
      "foo#bar",
    ]);
  });

  it("should handle Unicode / multi-byte characters", () => {
    expect(convertStrToList("こんにちは,世界")).toEqual(["こんにちは", "世界"]);
  });

  it("should handle items that are numbers as strings", () => {
    expect(convertStrToList("1,2,3")).toEqual(["1", "2", "3"]);
  });

  // ── Boundary / regression cases ───────────────────────────────────────────

  it("should handle a string of exactly length 2 with a comma delimiter", () => {
    expect(convertStrToList("a,b")).toEqual(["a", "b"]);
  });

  it("should handle Windows-style CRLF line endings by leaving \\r in values", () => {
    const result = convertStrToList("foo\r\nbar\r\nbaz");
    expect(result).toEqual(["foo", "bar", "baz"]);
  });
  it("should return the original string (trimmed) when it contains only spaces and no delimiter", () => {
    expect(convertStrToList("no delimiters here")).toEqual([
      "no delimiters here",
    ]);
  });
});