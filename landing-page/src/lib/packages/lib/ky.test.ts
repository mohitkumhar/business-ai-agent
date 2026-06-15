import { describe, expect, it, mock, beforeEach, afterEach } from "bun:test";
import type { Mock } from "bun:test";
import { rebuildFetchWithoutChunkedEncoding } from "./ky";

describe("rebuildFetchWithoutChunkedEncoding", () => {
  let originalFetch: typeof globalThis.fetch;
  let mockFetch: Mock<typeof globalThis.fetch>;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    mockFetch = mock((..._args: Parameters<typeof globalThis.fetch>) => Promise.resolve(new Response("ok"))) as Mock<typeof globalThis.fetch>;
    globalThis.fetch = mockFetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("should pass through string input unchanged", async () => {
    await rebuildFetchWithoutChunkedEncoding("https://example.com", { method: "POST" });
    expect(mockFetch).toHaveBeenCalledWith("https://example.com", { method: "POST" });
  });

  it("should pass through URL input unchanged", async () => {
    const url = new URL("https://example.com");
    await rebuildFetchWithoutChunkedEncoding(url, { method: "GET" });
    expect(mockFetch).toHaveBeenCalledWith(url, { method: "GET" });
  });

  it("should reconstruct Request object to avoid chunked encoding", async () => {
    const request = new Request("https://example.com", {
      method: "POST",
      headers: { "x-custom": "1" },
      body: "test body",
    });

    await rebuildFetchWithoutChunkedEncoding(request, {
      headers: { "x-override": "2" },
      mode: "cors",
    });

    expect(mockFetch).toHaveBeenCalled();
    const [url, init] = mockFetch.mock.calls[0];
    
    expect(url).toBe("https://example.com/");
    expect(init).toBeDefined();
    expect(init!.method).toBe("POST");
    expect(init!.mode).toBe("cors");
    
    // Check headers
    expect(init!.headers).toBeInstanceOf(Headers);
    expect((init!.headers as Headers).get("x-custom")).toBe("1");
    expect((init!.headers as Headers).get("x-override")).toBe("2");
    
    // Check body
    expect(init!.body).toBeInstanceOf(ArrayBuffer);
    const bodyString = new TextDecoder().decode(init!.body as ArrayBuffer);
    expect(bodyString).toBe("test body");
    
    // Check duplex
    expect((init as any).duplex).toBe("half");
  });

  it("should throw if Request body is already consumed", async () => {
    const request = new Request("https://example.com", {
      method: "POST",
      body: "test body",
    });
    
    await request.text(); // Consume body
    expect(request.bodyUsed).toBe(true);

    expect(rebuildFetchWithoutChunkedEncoding(request)).rejects.toThrow("Request body already consumed");
  });

  it("should correctly handle requests without body", async () => {
    const request = new Request("https://example.com", {
      method: "GET",
      headers: { "x-custom": "1" },
    });

    await rebuildFetchWithoutChunkedEncoding(request);

    expect(mockFetch).toHaveBeenCalled();
    const [url, init] = mockFetch.mock.calls[0];
    
    expect(url).toBe("https://example.com/");
    expect(init).toBeDefined();
    expect(init!.method).toBe("GET");
    expect(init!.body).toBeUndefined();
    expect((init as any).duplex).toBeUndefined();
  });
  
  it("should prefer init properties over Request properties", async () => {
    const request = new Request("https://example.com", {
      method: "GET",
      mode: "cors",
    });

    await rebuildFetchWithoutChunkedEncoding(request, {
      method: "POST",
      mode: "no-cors",
      body: "init body",
      duplex: "full",
    });

    expect(mockFetch).toHaveBeenCalled();
    const [url, init] = mockFetch.mock.calls[0];
    
    expect(init).toBeDefined();
    expect(init!.method).toBe("POST");
    expect(init!.mode).toBe("no-cors");
    expect(init!.body).toBe("init body");
    expect((init as any).duplex).toBe("full");
  });
});
