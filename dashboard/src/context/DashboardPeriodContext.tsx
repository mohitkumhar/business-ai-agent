"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { DashboardPeriod } from "@/lib/dashboardPeriod";
import {
  DASHBOARD_REFRESH_EVENT,
  consumeDashboardRefreshPending,
} from "@/lib/dashboardRefresh";

type DashboardPeriodContextValue = {
  period: DashboardPeriod;
  setPeriod: (p: DashboardPeriod) => void;
  /** Bump to refetch all dashboard API data (import success, manual refresh). */
  dataVersion: number;
  bumpDataVersion: () => void;
};

const DashboardPeriodContext = createContext<DashboardPeriodContextValue | null>(null);

export function DashboardPeriodProvider({ children }: { children: ReactNode }) {
  const [period, setPeriod] = useState<DashboardPeriod>("this_month");
  const [dataVersion, setDataVersion] = useState(0);
  const bumpDataVersion = useCallback(() => {
    setDataVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      if (consumeDashboardRefreshPending()) {
        bumpDataVersion();
      }
    });
  }, [bumpDataVersion]);

  useEffect(() => {
    const onRefresh = () => bumpDataVersion();
    window.addEventListener(DASHBOARD_REFRESH_EVENT, onRefresh);
    return () => window.removeEventListener(DASHBOARD_REFRESH_EVENT, onRefresh);
  }, [bumpDataVersion]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState !== "visible") return;
      if (consumeDashboardRefreshPending()) {
        bumpDataVersion();
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [bumpDataVersion]);

  const value = useMemo(
    () => ({ period, setPeriod, dataVersion, bumpDataVersion }),
    [period, dataVersion, bumpDataVersion],
  );
  return (
    <DashboardPeriodContext.Provider value={value}>
      {children}
    </DashboardPeriodContext.Provider>
  );
}

export function useDashboardPeriod(): DashboardPeriodContextValue {
  const ctx = useContext(DashboardPeriodContext);
  if (!ctx) {
    throw new Error("useDashboardPeriod must be used within DashboardPeriodProvider");
  }
  return ctx;
}
