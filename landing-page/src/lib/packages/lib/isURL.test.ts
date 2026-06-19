import { describe, expect, it } from "bun:test";
import { isURL } from "./isURL";

describe("isURL", () => {
  it("valid HTTP URL", () => {
    expect(isURL("http://example.com")).toBe(true);
  });

  it("valid HTTPS URL", () => {
    expect(isURL("https://example.com/path?x=1#frag")).toBe(true);
  });

  it("invalid URL without protocol", () => {
    expect(isURL("example.com")).toBe(false);
  });

  it("invalid FTP URL (protocol not allowed)", () => {
    expect(isURL("ftp://example.com")).toBe(false);
  });

  it("empty string returns false", () => {
    expect(isURL("")).toBe(false);
  });

  it("option override: require_protocol false allows protocol-less urls", () => {
    expect(isURL("example.com", { require_protocol: false })).toBe(true);
  });
});
