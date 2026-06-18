// testEnvironment is "node" — window and sessionStorage are undefined by default.
// SSR-guard tests need no setup; browser-path tests call setupBrowserEnv().
// Pre-seeding `store` directly avoids inflating setItem call-counts in assertions.

import {
  DASHBOARD_REFRESH_EVENT,
  markDashboardRefreshPending,
  consumeDashboardRefreshPending,
  dispatchDashboardRefresh,
} from "../dashboardRefresh";

let store: Record<string, string> = {};

const sessionStorageMock = {
  getItem: jest.fn((key: string): string | null => store[key] ?? null),
  setItem: jest.fn((key: string, value: string): void => {
    store[key] = value;
  }),
  removeItem: jest.fn((key: string): void => {
    delete store[key];
  }),
};

const dispatchEventMock = jest.fn();

function setupBrowserEnv(): void {
  store = {};
  sessionStorageMock.getItem.mockClear();
  sessionStorageMock.setItem.mockClear();
  sessionStorageMock.removeItem.mockClear();
  dispatchEventMock.mockClear();

  Object.defineProperty(global, "window", {
    value: { dispatchEvent: dispatchEventMock },
    writable: true,
    configurable: true,
  });
  Object.defineProperty(global, "sessionStorage", {
    value: sessionStorageMock,
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
  Object.defineProperty(global, "sessionStorage", {
    value: undefined,
    writable: true,
    configurable: true,
  });
}

describe("DASHBOARD_REFRESH_EVENT", () => {
  it("equals 'profitpilot-dashboard-refresh'", () => {
    expect(DASHBOARD_REFRESH_EVENT).toBe("profitpilot-dashboard-refresh");
  });
});

describe("markDashboardRefreshPending", () => {
  afterEach(() => {
    teardownBrowserEnv();
  });

  describe("SSR guard (window undefined)", () => {
    it("returns without throwing when window is undefined", () => {
      expect(() => markDashboardRefreshPending()).not.toThrow();
    });

    it("never touches sessionStorage when window is undefined", () => {
      markDashboardRefreshPending();
      expect(sessionStorageMock.setItem).not.toHaveBeenCalled();
    });
  });

  describe("normal behaviour (browser env)", () => {
    it("writes the pending key with value '1' to sessionStorage", () => {
      setupBrowserEnv();
      markDashboardRefreshPending();
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        "profitpilot_pending_dashboard_refresh",
        "1"
      );
    });

    it("calls sessionStorage.setItem exactly once", () => {
      setupBrowserEnv();
      markDashboardRefreshPending();
      expect(sessionStorageMock.setItem).toHaveBeenCalledTimes(1);
    });
  });

  describe("silent catch — sessionStorage.setItem throws", () => {
    it("does not propagate the exception", () => {
      setupBrowserEnv();
      sessionStorageMock.setItem.mockImplementationOnce(() => {
        throw new DOMException("QuotaExceededError");
      });
      expect(() => markDashboardRefreshPending()).not.toThrow();
    });
  });
});

describe("consumeDashboardRefreshPending", () => {
  afterEach(() => {
    teardownBrowserEnv();
  });

  describe("SSR guard (window undefined)", () => {
    it("returns false when window is undefined", () => {
      expect(consumeDashboardRefreshPending()).toBe(false);
    });

    it("never reads or removes from sessionStorage when window is undefined", () => {
      consumeDashboardRefreshPending();
      expect(sessionStorageMock.getItem).not.toHaveBeenCalled();
      expect(sessionStorageMock.removeItem).not.toHaveBeenCalled();
    });
  });

  describe("pending key is set to '1'", () => {
    it("returns true when the pending key is present", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "1";
      expect(consumeDashboardRefreshPending()).toBe(true);
    });

    it("removes the pending key from sessionStorage after consuming", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "1";
      consumeDashboardRefreshPending();
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith(
        "profitpilot_pending_dashboard_refresh"
      );
    });

    it("calls sessionStorage.removeItem exactly once", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "1";
      consumeDashboardRefreshPending();
      expect(sessionStorageMock.removeItem).toHaveBeenCalledTimes(1);
    });
  });

  describe("pending key is absent", () => {
    it("returns false when the key is not in sessionStorage", () => {
      setupBrowserEnv();
      // store is empty — getItem returns null
      expect(consumeDashboardRefreshPending()).toBe(false);
    });

    it("does not call sessionStorage.removeItem when the key is absent", () => {
      setupBrowserEnv();
      consumeDashboardRefreshPending();
      expect(sessionStorageMock.removeItem).not.toHaveBeenCalled();
    });
  });

  describe("pending key has an unexpected (non-'1') value", () => {
    it("returns false when the stored value is 'true' instead of '1'", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "true";
      expect(consumeDashboardRefreshPending()).toBe(false);
    });

    it("returns false when the stored value is '0'", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "0";
      expect(consumeDashboardRefreshPending()).toBe(false);
    });

    it("does not call removeItem when the value is not exactly '1'", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "yes";
      consumeDashboardRefreshPending();
      expect(sessionStorageMock.removeItem).not.toHaveBeenCalled();
    });
  });

  describe("idempotency — second call after consumption", () => {
    it("returns false on the second call because the key was removed by the first", () => {
      setupBrowserEnv();
      store["profitpilot_pending_dashboard_refresh"] = "1";
      consumeDashboardRefreshPending(); // consumes
      expect(consumeDashboardRefreshPending()).toBe(false);
    });
  });

  describe("silent catch — sessionStorage.getItem throws", () => {
    it("does not propagate the exception", () => {
      setupBrowserEnv();
      sessionStorageMock.getItem.mockImplementationOnce(() => {
        throw new DOMException("SecurityError");
      });
      expect(() => consumeDashboardRefreshPending()).not.toThrow();
    });

    it("returns false when sessionStorage.getItem throws", () => {
      setupBrowserEnv();
      sessionStorageMock.getItem.mockImplementationOnce(() => {
        throw new DOMException("SecurityError");
      });
      expect(consumeDashboardRefreshPending()).toBe(false);
    });
  });
});

describe("dispatchDashboardRefresh", () => {
  afterEach(() => {
    teardownBrowserEnv();
  });

  describe("SSR guard (window undefined)", () => {
    it("returns without throwing when window is undefined", () => {
      expect(() => dispatchDashboardRefresh()).not.toThrow();
    });

    it("does not write to sessionStorage when window is undefined", () => {
      dispatchDashboardRefresh();
      expect(sessionStorageMock.setItem).not.toHaveBeenCalled();
    });

    it("does not dispatch any window event when window is undefined", () => {
      dispatchDashboardRefresh();
      expect(dispatchEventMock).not.toHaveBeenCalled();
    });
  });

  describe("normal behaviour (browser env)", () => {
    it("marks the refresh pending in sessionStorage", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        "profitpilot_pending_dashboard_refresh",
        "1"
      );
    });

    it("dispatches exactly one window event", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      expect(dispatchEventMock).toHaveBeenCalledTimes(1);
    });

    it("dispatches an Event whose type equals DASHBOARD_REFRESH_EVENT", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      const dispatched = dispatchEventMock.mock.calls[0][0] as Event;
      expect(dispatched.type).toBe(DASHBOARD_REFRESH_EVENT);
    });

    it("dispatches a plain Event instance (not a subclass)", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      const dispatched = dispatchEventMock.mock.calls[0][0] as Event;
      expect(dispatched).toBeInstanceOf(Event);
    });
  });

  describe("call order — sessionStorage is written before the event fires", () => {
    it("sessionStorage.setItem is called before window.dispatchEvent", () => {
      setupBrowserEnv();
      const callOrder: string[] = [];

      sessionStorageMock.setItem.mockImplementationOnce(
        (key: string, value: string) => {
          store[key] = value;
          callOrder.push("setItem");
        }
      );
      dispatchEventMock.mockImplementationOnce(() => {
        callOrder.push("dispatchEvent");
      });

      dispatchDashboardRefresh();
      expect(callOrder).toEqual(["setItem", "dispatchEvent"]);
    });
  });

  describe("integration — pending flag is consumable after dispatch", () => {
    it("consumeDashboardRefreshPending returns true immediately after dispatchDashboardRefresh", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      expect(consumeDashboardRefreshPending()).toBe(true);
    });

    it("consumeDashboardRefreshPending returns false on the second call after dispatch", () => {
      setupBrowserEnv();
      dispatchDashboardRefresh();
      consumeDashboardRefreshPending(); // first consume
      expect(consumeDashboardRefreshPending()).toBe(false);
    });
  });
});