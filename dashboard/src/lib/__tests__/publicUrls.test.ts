/**
 * Regression tests for dashboard/src/lib/publicUrls.ts
 *
 * Both exports are module-level constants evaluated at require() time.
 * Each test sets process.env, calls jest.resetModules(), then require()s
 * the module fresh so constants are re-evaluated under the new env.
 */

type PublicUrls = { LANDING_PAGE_URL: string; AGENT_API_BASE: string };

function loadModule(env: {
  NEXT_PUBLIC_LANDING_URL?: string;
  NEXT_PUBLIC_AGENT_API_URL?: string;
}): PublicUrls {
  const KEYS = ["NEXT_PUBLIC_LANDING_URL", "NEXT_PUBLIC_AGENT_API_URL"] as const;

  const saved: Record<string, string | undefined> = {};
  for (const key of KEYS) {
    saved[key] = process.env[key];
  }

  for (const key of KEYS) {
    if (key in env && env[key] !== undefined) {
      process.env[key] = env[key] as string;
    } else {
      delete process.env[key];
    }
  }

  jest.resetModules();
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require("../publicUrls") as PublicUrls;

  for (const key of KEYS) {
    if (saved[key] === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = saved[key];
    }
  }

  return mod;
}

const DEFAULT_LANDING = "http://localhost:5173";

describe("LANDING_PAGE_URL", () => {
  describe("fallback to default", () => {
    it("returns the default when env var is not set", () => {
      const { LANDING_PAGE_URL } = loadModule({});
      expect(LANDING_PAGE_URL).toBe(DEFAULT_LANDING);
    });

    it("returns the default when env var is an empty string", () => {
      const { LANDING_PAGE_URL } = loadModule({ NEXT_PUBLIC_LANDING_URL: "" });
      expect(LANDING_PAGE_URL).toBe(DEFAULT_LANDING);
    });

    it("returns the default when env var is whitespace only", () => {
      const { LANDING_PAGE_URL } = loadModule({ NEXT_PUBLIC_LANDING_URL: "   " });
      expect(LANDING_PAGE_URL).toBe(DEFAULT_LANDING);
    });
  });

  describe("Grafana port-3000 guard", () => {
    it("blocks http://localhost:3000", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "http://localhost:3000",
      });
      expect(LANDING_PAGE_URL).toBe(DEFAULT_LANDING);
    });

    it("blocks http://127.0.0.1:3000", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "http://127.0.0.1:3000",
      });
      expect(LANDING_PAGE_URL).toBe(DEFAULT_LANDING);
    });

    it("does NOT block http://localhost:3000/ — guard is exact string match, trailing slash bypasses it", () => {
      // .replace() then strips the slash, so the result is "http://localhost:3000"
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "http://localhost:3000/",
      });
      expect(LANDING_PAGE_URL).toBe("http://localhost:3000");
    });

    it("does not block port 30000", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "http://localhost:30000",
      });
      expect(LANDING_PAGE_URL).toBe("http://localhost:30000");
    });

    it("does not block port 3001", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "http://localhost:3001",
      });
      expect(LANDING_PAGE_URL).toBe("http://localhost:3001");
    });
  });

  describe("trailing slash normalisation", () => {
    it("strips a trailing slash", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "https://marketing.example.com/",
      });
      expect(LANDING_PAGE_URL).toBe("https://marketing.example.com");
    });

    it("returns a URL without trailing slash unchanged", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "https://marketing.example.com",
      });
      expect(LANDING_PAGE_URL).toBe("https://marketing.example.com");
    });

    it("strips only the final slash when multiple trailing slashes are present", () => {
      // .replace(/\/$/, "") matches one slash at end-of-string, not all of them
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "https://example.com//",
      });
      expect(LANDING_PAGE_URL).toBe("https://example.com/");
    });

    it("preserves a sub-path after stripping the trailing slash", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "https://example.com/marketing/",
      });
      expect(LANDING_PAGE_URL).toBe("https://example.com/marketing");
    });
  });

  describe("whitespace trimming", () => {
    it("trims surrounding spaces before evaluating the URL", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "  https://example.com  ",
      });
      expect(LANDING_PAGE_URL).toBe("https://example.com");
    });

    it("trims spaces and strips a trailing slash when both are present", () => {
      const { LANDING_PAGE_URL } = loadModule({
        NEXT_PUBLIC_LANDING_URL: "  https://example.com/  ",
      });
      expect(LANDING_PAGE_URL).toBe("https://example.com");
    });
  });
});

describe("AGENT_API_BASE", () => {
  it("is an empty string when env var is not set", () => {
    const { AGENT_API_BASE } = loadModule({});
    expect(AGENT_API_BASE).toBe("");
  });

  it("is an empty string when env var is an empty string", () => {
    const { AGENT_API_BASE } = loadModule({ NEXT_PUBLIC_AGENT_API_URL: "" });
    expect(AGENT_API_BASE).toBe("");
  });

  it("strips a trailing slash", () => {
    const { AGENT_API_BASE } = loadModule({
      NEXT_PUBLIC_AGENT_API_URL: "http://backend:5000/",
    });
    expect(AGENT_API_BASE).toBe("http://backend:5000");
  });

  it("returns a URL without trailing slash unchanged", () => {
    const { AGENT_API_BASE } = loadModule({
      NEXT_PUBLIC_AGENT_API_URL: "http://backend:5000",
    });
    expect(AGENT_API_BASE).toBe("http://backend:5000");
  });

  it("strips only the final slash when multiple trailing slashes are present", () => {
    const { AGENT_API_BASE } = loadModule({
      NEXT_PUBLIC_AGENT_API_URL: "http://backend:5000//",
    });
    expect(AGENT_API_BASE).toBe("http://backend:5000/");
  });

  it("preserves a cross-origin URL unchanged", () => {
    const { AGENT_API_BASE } = loadModule({
      NEXT_PUBLIC_AGENT_API_URL: "https://api.staging.example.com/v1",
    });
    expect(AGENT_API_BASE).toBe("https://api.staging.example.com/v1");
  });
})