import { describe, expect, it } from "bun:test";
import { validateHttpReqHeaders } from "./validateHttpReqUrl";

describe("validateHttpReqHeaders", () => {
  describe("IMDSv2 token headers", () => {
    it("should block X-aws-ec2-metadata-token header", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "X-aws-ec2-metadata-token",
            value: "some-token",
          },
        ]),
      ).toThrow("bypass cloud metadata service");
    });

    it("should block X-aws-ec2-metadata-token-ttl-seconds header", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "X-aws-ec2-metadata-token-ttl-seconds",
            value: "21600",
          },
        ]),
      ).toThrow("bypass cloud metadata service");
    });

    it("should be case-insensitive", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "x-AWS-ec2-METADATA-token",
            value: "some-token",
          },
        ]),
      ).toThrow("bypass cloud metadata service");
    });
  });

  describe("Google Cloud metadata headers", () => {
    it("should block Metadata-Flavor header", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "Metadata-Flavor",
            value: "Google",
          },
        ]),
      ).toThrow("bypass cloud metadata service");
    });

    it("should block Metadata header", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "Metadata",
            value: "true",
          },
        ]),
      ).toThrow("bypass cloud metadata service");
    });
  });

  describe("Valid headers", () => {
    it("should allow standard headers", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "Content-Type",
            value: "application/json",
          },
          {
            key: "Authorization",
            value: "Bearer token",
          },
        ]),
      ).not.toThrow();
    });

    it("should allow custom application headers", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            key: "X-Custom-Header",
            value: "custom-value",
          },
        ]),
      ).not.toThrow();
    });

    it("should handle undefined headers", () => {
      expect(() => validateHttpReqHeaders(undefined)).not.toThrow();
    });

    it("should handle empty headers array", () => {
      expect(() => validateHttpReqHeaders([])).not.toThrow();
    });

    it("should skip headers without a key", () => {
      expect(() =>
        validateHttpReqHeaders([
          {
            value: "some-value",
          },
        ]),
      ).not.toThrow();
    });
  });
});