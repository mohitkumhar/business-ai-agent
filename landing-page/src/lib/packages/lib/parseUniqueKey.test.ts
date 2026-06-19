import { describe, expect, it } from "bun:test";
import { parseUniqueKey } from "./parseUniqueKey";

describe("parseUniqueKey", () => {
  describe("Basic Functionality", () => {
    it("should return the key itself if existingKeys is empty", () => {
      expect(parseUniqueKey("hello", [])).toBe("hello");
      expect(parseUniqueKey("my-key", [])).toBe("my-key");
    });

    it("should return the key with (1) suffix if the key is already in existingKeys", () => {
      expect(parseUniqueKey("hello", ["hello"])).toBe("hello (1)");
    });

    it("should increment the suffix index based on the count of matching keys", () => {
      expect(parseUniqueKey("hello", ["hello", "hello (1)"])).toBe("hello (2)");
      expect(parseUniqueKey("hello", ["hello", "hello (1)", "hello (2)"])).toBe("hello (3)");
    });
  });

  describe("Suffix Stripping & Collision Resolution", () => {
    it("should strip existing (number) suffix if no collision is present", () => {
      expect(parseUniqueKey("hello (5)", [])).toBe("hello");
    });

    it("should resolve collisions properly when the input already has a suffix", () => {
      expect(parseUniqueKey("hello (5)", ["hello"])).toBe("hello (1)");
      expect(parseUniqueKey("hello (10)", ["hello", "hello (1)"])).toBe("hello (2)");
    });

    it("should resolve collisions properly when both prefix and suffixed keys exist", () => {
      expect(parseUniqueKey("hello (5)", ["hello", "hello (1)"])).toBe("hello (2)");
    });
  });

  describe("Edge Cases & Formatting", () => {
    it("should handle keys with spaces inside but no digits in parentheses", () => {
      expect(parseUniqueKey("hello (abc)", [])).toBe("hello (abc)");
      expect(parseUniqueKey("hello (abc)", ["hello (abc)"])).toBe("hello (abc) (1)");
    });

    it("should match keys with extra whitespace before the parentheses", () => {
      expect(parseUniqueKey("hello  (2)", ["hello"])).toBe("hello (1)");
    });

    it("should match keys with no whitespace before the parentheses", () => {
      expect(parseUniqueKey("hello(2)", ["hello"])).toBe("hello (1)");
    });

    it("should handle empty string input correctly", () => {
      expect(parseUniqueKey("", [])).toBe("");
    });

    it("should handle collisions with empty string", () => {
      expect(parseUniqueKey("", [""])).toBe(" (1)");
    });

    it("should handle multiple levels of parentheses", () => {
      expect(parseUniqueKey("hello (1) (2)", [])).toBe("hello (1)");
      expect(parseUniqueKey("hello (1) (2)", ["hello (1)"])).toBe("hello (1) (1)");
    });

    it("should not conflict with keys that have similar prefixes but different characters", () => {
      expect(parseUniqueKey("hello", ["hello-world", "hello_world"])).toBe("hello");
    });
  });
});
