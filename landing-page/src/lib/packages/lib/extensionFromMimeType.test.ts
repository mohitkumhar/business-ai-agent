import { describe, expect, it } from "bun:test";
import {
  extensionFromMimeType,
  parseAllowedFileTypesMetadata,
} from "./extensionFromMimeType";

describe("extensionFromMimeType", () => {
  it("should return correct extension for audio types", () => {
    expect(extensionFromMimeType["audio/mpeg"]).toBe("mp3");
    expect(extensionFromMimeType["audio/wav"]).toBe("wav");
    expect(extensionFromMimeType["audio/ogg"]).toBe("ogg");
  });

  it("should return correct extension for image types", () => {
    expect(extensionFromMimeType["image/jpeg"]).toBe("jpeg");
    expect(extensionFromMimeType["image/png"]).toBe("png");
    expect(extensionFromMimeType["image/gif"]).toBe("gif");
    expect(extensionFromMimeType["image/svg+xml"]).toBe("svg");
    expect(extensionFromMimeType["image/webp"]).toBe("webp");
  });

  it("should return correct extension for video types", () => {
    expect(extensionFromMimeType["video/mp4"]).toBe("mp4");
    expect(extensionFromMimeType["video/webm"]).toBe("webm");
    expect(extensionFromMimeType["video/quicktime"]).toBe("mov");
  });

  it("should return correct extension for application types", () => {
    expect(extensionFromMimeType["application/pdf"]).toBe("pdf");
    expect(extensionFromMimeType["application/json"]).toBe("json");
    expect(extensionFromMimeType["application/javascript"]).toBe("js");
    expect(extensionFromMimeType["application/zip"]).toBe("zip");
    expect(extensionFromMimeType["application/xml"]).toBe("xml");
  });

  it("should return undefined for unknown MIME types", () => {
    expect(extensionFromMimeType["unknown/type"]).toBeUndefined();
    expect(extensionFromMimeType[""]).toBeUndefined();
  });

  it("should contain all expected MIME type entries", () => {
    const entries = Object.keys(extensionFromMimeType);
    expect(entries.length).toBeGreaterThan(0);
    expect(entries).toContain("image/jpeg");
    expect(entries).toContain("application/pdf");
    expect(entries).toContain("video/mp4");
    expect(entries).toContain("audio/mpeg");
  });
});

describe("parseAllowedFileTypesMetadata", () => {
  it("should return matching entries for specific extensions", () => {
    const result = parseAllowedFileTypesMetadata(["pdf", "png"]);

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ mimeType: "application/pdf", extension: "pdf" }),
        expect.objectContaining({ mimeType: "image/png", extension: "png" }),
      ]),
    );
    expect(result).toHaveLength(2);
  });

  it("should return all matching image types for image/* wildcard", () => {
    const result = parseAllowedFileTypesMetadata(["image/*"]);

    expect(result.length).toBeGreaterThan(0);
    result.forEach((entry) => {
      expect(entry.mimeType.startsWith("image/")).toBe(true);
    });
  });

  it("should handle mixed wildcards and specific extensions", () => {
    const result = parseAllowedFileTypesMetadata(["image/*", "pdf"]);

    const imageEntries = result.filter((e) => e.mimeType.startsWith("image/"));
    expect(imageEntries.length).toBeGreaterThan(0);

    expect(result).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ mimeType: "application/pdf", extension: "pdf" }),
      ]),
    );
  });

  it("should return empty array when allowedFileTypes is empty", () => {
    const result = parseAllowedFileTypesMetadata([]);
    expect(result).toEqual([]);
  });

  it("should return empty array when no extensions match", () => {
    const result = parseAllowedFileTypesMetadata(["nonexistent"]);
    expect(result).toEqual([]);
  });

  it("should use exact extension matching (json should not match js)", () => {
    const result = parseAllowedFileTypesMetadata(["json"]);

    expect(result).toEqual([
      expect.objectContaining({ mimeType: "application/json", extension: "json" }),
    ]);
    expect(result).toHaveLength(1);
  });

  it("should handle multiple wildcards from different base types", () => {
    const result = parseAllowedFileTypesMetadata(["audio/*", "video/*"]);

    result.forEach((entry) => {
      const baseType = entry.mimeType.split("/")[0];
      expect(["audio", "video"]).toContain(baseType);
    });
  });

  it("should deduplicate entries when extension and wildcard overlap", () => {
    const result = parseAllowedFileTypesMetadata(["image/*", "png"]);

    const pngEntries = result.filter((e) => e.extension === "png");
    expect(pngEntries).toHaveLength(1);
  });
});
