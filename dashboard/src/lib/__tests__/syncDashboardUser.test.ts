/**
 * Regression tests for dashboard/src/lib/syncDashboardUser.ts
 *
 * Strategy:
 *  - Jest's testEnvironment is "node", so global.window is undefined by
 *    default. SSR-guard tests therefore need no setup at all — calling the
 *    functions in that state exercises the guard branch directly.
 *  - Browser-path tests call setupBrowserEnv() before the function under
 *    test, which defines a minimal global.window (with location.search and
 *    dispatchEvent) and a separate global.localStorage mock backed by a
 *    plain in-memory store.
 *  - Data can be pre-seeded by writing to `store` directly so that getItem
 *    returns it without polluting the setItem call-count used in assertions.
 *  - api.getBusinessInfo is mocked at the module level; mockReset() runs
 *    before each test in the syncUserNameFromApi suite so implementations
 *    never leak between tests.
 */

import { syncUserEmailFromUrl, syncUserNameFromApi } from "../syncDashboardUser";
import { api } from "../api";

// ---------------------------------------------------------------------------
// Module-level mock
// ---------------------------------------------------------------------------

jest.mock("../api", () => ({
  api: {
    getBusinessInfo: jest.fn(),
  },
}));

const mockGetBusinessInfo = api.getBusinessInfo as jest.Mock;

// ---------------------------------------------------------------------------
// Browser environment helpers
// ---------------------------------------------------------------------------

let store: Record<string, string> = {};

const localStorageMock = {
  getItem: jest.fn((key: string): string | null => store[key] ?? null),
  setItem: jest.fn((key: string, value: string): void => {
    store[key] = value;
  }),
};

const dispatchEventMock = jest.fn();

function setupBrowserEnv(search = ""): void {
  store = {};
  localStorageMock.getItem.mockClear();
  localStorageMock.setItem.mockClear();
  dispatchEventMock.mockClear();

  Object.defineProperty(global, "window", {
    value: { location: { search }, dispatchEvent: dispatchEventMock },
    writable: true,
    configurable: true,
  });
  Object.defineProperty(global, "localStorage", {
    value: localStorageMock,
    writable: true,
    configurable: true,
  });
}

function teardownBrowserEnv(): void {
  Object.defineProperty(global, "window", {
    value: undefined,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(global, "localStorage", {
    value: undefined,
    writable: true,
    configurable: true,
  });
}

// ---------------------------------------------------------------------------
// syncUserEmailFromUrl
// ---------------------------------------------------------------------------

describe("syncUserEmailFromUrl", () => {
  afterEach(() => {
    teardownBrowserEnv();
  });

  // ── SSR guard ─────────────────────────────────────────────────────────────

  describe("SSR guard (window undefined)", () => {
    it("returns immediately without throwing when window is undefined", () => {
      expect(() => syncUserEmailFromUrl()).not.toThrow();
    });

    it("never touches localStorage when window is undefined", () => {
      // localStorage itself is also undefined in node env — absence of
      // any ReferenceError confirms the early-return fired.
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  // ── No email in URL ───────────────────────────────────────────────────────

  describe("no user_email in the search string", () => {
    it("does nothing when the search string is empty", () => {
      setupBrowserEnv("");
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });

    it("does nothing when the search string contains unrelated params only", () => {
      setupBrowserEnv("?theme=dark&lang=en");
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });
  });

  // ── Normal write — localStorage empty ────────────────────────────────────

  describe("email in URL, localStorage starts empty", () => {
    it("stores the email under profit_pilot_user", () => {
      setupBrowserEnv("?user_email=new@test.com");
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "profit_pilot_user",
        JSON.stringify({ email: "new@test.com" })
      );
    });

    it("dispatches exactly one profitpilot-user event", () => {
      setupBrowserEnv("?user_email=new@test.com");
      syncUserEmailFromUrl();
      expect(dispatchEventMock).toHaveBeenCalledTimes(1);
    });
  });

  // ── Idempotency ───────────────────────────────────────────────────────────

  describe("idempotency — stored email already matches URL email", () => {
    it("skips the write when emails are identical", () => {
      setupBrowserEnv("?user_email=same@test.com");
      store["profit_pilot_user"] = JSON.stringify({ email: "same@test.com" });
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it("skips the event dispatch when emails are identical", () => {
      setupBrowserEnv("?user_email=same@test.com");
      store["profit_pilot_user"] = JSON.stringify({ email: "same@test.com" });
      syncUserEmailFromUrl();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });
  });

  // ── Merging — existing data preserved ────────────────────────────────────

  describe("merging — existing localStorage user object is preserved", () => {
    it("updates email while keeping all other stored fields", () => {
      setupBrowserEnv("?user_email=updated@test.com");
      store["profit_pilot_user"] = JSON.stringify({
        email: "old@test.com",
        full_name: "Jane Doe",
        role: "admin",
      });
      syncUserEmailFromUrl();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[0][1] as string
      );
      expect(stored.email).toBe("updated@test.com");
      expect(stored.full_name).toBe("Jane Doe");
      expect(stored.role).toBe("admin");
    });

    it("dispatches a profitpilot-user event after merging", () => {
      setupBrowserEnv("?user_email=updated@test.com");
      store["profit_pilot_user"] = JSON.stringify({ email: "old@test.com" });
      syncUserEmailFromUrl();
      expect(dispatchEventMock).toHaveBeenCalledTimes(1);
    });

    it("correctly extracts user_email when other query params are also present", () => {
      setupBrowserEnv("?theme=dark&user_email=multi@test.com&lang=en");
      syncUserEmailFromUrl();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[0][1] as string
      );
      expect(stored.email).toBe("multi@test.com");
    });
  });

  // ── Catch fallback — corrupted JSON in localStorage ───────────────────────

  describe("catch path — JSON.parse fails on stored value", () => {
    it("falls back to storing only { email } when the stored string is not valid JSON", () => {
      setupBrowserEnv("?user_email=fallback@test.com");
      store["profit_pilot_user"] = "NOT_VALID_JSON{{{";
      syncUserEmailFromUrl();
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "profit_pilot_user",
        JSON.stringify({ email: "fallback@test.com" })
      );
    });

    it("still dispatches profitpilot-user event in the catch path", () => {
      setupBrowserEnv("?user_email=fallback@test.com");
      store["profit_pilot_user"] = "NOT_VALID_JSON{{{";
      syncUserEmailFromUrl();
      expect(dispatchEventMock).toHaveBeenCalledTimes(1);
    });
  });
});

// ---------------------------------------------------------------------------
// syncUserNameFromApi
// ---------------------------------------------------------------------------

describe("syncUserNameFromApi", () => {
  beforeEach(() => {
    mockGetBusinessInfo.mockReset();
  });

  afterEach(() => {
    teardownBrowserEnv();
  });

  // ── SSR guard ─────────────────────────────────────────────────────────────

  describe("SSR guard (window undefined)", () => {
    it("resolves without calling api.getBusinessInfo when window is undefined", async () => {
      await syncUserNameFromApi();
      expect(mockGetBusinessInfo).not.toHaveBeenCalled();
    });

    it("resolves without throwing when window is undefined", async () => {
      await expect(syncUserNameFromApi()).resolves.toBeUndefined();
    });
  });

  // ── Happy path ────────────────────────────────────────────────────────────

  describe("happy path — API returns a valid user_name", () => {
    it("stores full_name in localStorage", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: "jane@corp.com",
      });
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).toHaveBeenCalled();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(stored.full_name).toBe("Jane Doe");
    });

    it("dispatches exactly one profitpilot-user event on success", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: "jane@corp.com",
      });
      await syncUserNameFromApi();
      // syncUserEmailFromUrl fires no event (empty search) — only syncUserNameFromApi does
      expect(dispatchEventMock).toHaveBeenCalledTimes(1);
    });

    it("uses user_email from the API response when it is present", async () => {
      setupBrowserEnv("");
      store["profit_pilot_user"] = JSON.stringify({ email: "local@corp.com" });
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: "api@corp.com",
      });
      await syncUserNameFromApi();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(stored.email).toBe("api@corp.com");
    });

    it("falls back to localStorage email when API user_email is null", async () => {
      setupBrowserEnv("");
      store["profit_pilot_user"] = JSON.stringify({ email: "local@corp.com" });
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: null,
      });
      await syncUserNameFromApi();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(stored.email).toBe("local@corp.com");
    });

    it("preserves all existing localStorage fields when merging full_name", async () => {
      setupBrowserEnv("");
      store["profit_pilot_user"] = JSON.stringify({
        email: "user@corp.com",
        role: "admin",
        theme: "dark",
      });
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: "user@corp.com",
      });
      await syncUserNameFromApi();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(stored.full_name).toBe("Jane Doe");
      expect(stored.email).toBe("user@corp.com");
      expect(stored.role).toBe("admin");
      expect(stored.theme).toBe("dark");
    });

    it("defaults localStorage base to empty object when profit_pilot_user is null", async () => {
      setupBrowserEnv("");
      // store is empty — getItem returns null, code uses || "{}"
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: "jane@corp.com",
      });
      await syncUserNameFromApi();
      const stored = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(stored.full_name).toBe("Jane Doe");
      expect(stored.email).toBe("jane@corp.com");
    });
  });

  // ── Early-return conditions ───────────────────────────────────────────────

  describe("early return — user_name missing or blank", () => {
    it("skips write and event when user_name is an empty string", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce({ user_name: "" });
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });

    it("skips write and event when user_name is whitespace-only (trim guard)", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce({ user_name: "   " });
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });

    it("skips write and event when user_name is null (optional-chain guard)", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce({ user_name: null });
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it("skips write and event when the API resolves with null (optional-chain on b)", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockResolvedValueOnce(null);
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  // ── Error swallowing ──────────────────────────────────────────────────────

  describe("error swallowing — API rejection is silently caught", () => {
    it("resolves without throwing when api.getBusinessInfo rejects", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockRejectedValueOnce(new Error("Network error"));
      await expect(syncUserNameFromApi()).resolves.toBeUndefined();
    });

    it("does not write to localStorage when the API rejects", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockRejectedValueOnce(new Error("Offline"));
      await syncUserNameFromApi();
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });

    it("does not dispatch an event when the API rejects", async () => {
      setupBrowserEnv("");
      mockGetBusinessInfo.mockRejectedValueOnce(new Error("Offline"));
      await syncUserNameFromApi();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });
  });

  // ── syncUserEmailFromUrl integration ──────────────────────────────────────

  describe("integration — syncUserEmailFromUrl is called before the API fetch", () => {
    it("writes URL email to localStorage before the API merge step", async () => {
      setupBrowserEnv("?user_email=from-url@corp.com");
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: null, // force fallback to localStorage email
      });
      await syncUserNameFromApi();
      // First setItem call originates from syncUserEmailFromUrl
      const firstWrite = JSON.parse(
        localStorageMock.setItem.mock.calls[0][1] as string
      );
      expect(firstWrite.email).toBe("from-url@corp.com");
    });

    it("URL email is available to the merge step via the localStorage fallback", async () => {
      setupBrowserEnv("?user_email=from-url@corp.com");
      mockGetBusinessInfo.mockResolvedValueOnce({
        user_name: "Jane Doe",
        user_email: null,
      });
      await syncUserNameFromApi();
      // Final setItem call originates from syncUserNameFromApi merge
      const lastWrite = JSON.parse(
        localStorageMock.setItem.mock.calls[
          localStorageMock.setItem.mock.calls.length - 1
        ][1] as string
      );
      expect(lastWrite.full_name).toBe("Jane Doe");
      expect(lastWrite.email).toBe("from-url@corp.com");
    });
  });
});