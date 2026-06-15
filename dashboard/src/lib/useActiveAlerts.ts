"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Alert } from "@/lib/api";

export function useActiveAlerts(): {
  alertsOpen: boolean;
  alertRows: Alert[];
  alertsLoading: boolean;
  openAlerts: () => void;
  closeAlerts: () => void;
} {
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [alertRows, setAlertRows] = useState<Alert[]>([]);
  const [alertsStatus, setAlertsStatus] = useState<"idle" | "loading" | "loaded">("idle");
  const alertsLoading = alertsStatus === "loading";

  const openAlerts = () => {
    setAlertsStatus("loading");
    setAlertsOpen(true);
  };

  const closeAlerts = () => {
    setAlertsOpen(false);
  };

  useEffect(() => {
    if (alertsStatus !== "loading") return;
    let cancelled = false;
    api
      .getAlertsList()
      .then((r) => {
        if (!cancelled) {
          setAlertRows(r.alerts || []);
        }
      })
      .catch(console.error)
      .finally(() => {
        if (!cancelled) {
          setAlertsStatus("loaded");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [alertsStatus]);

  useEffect(() => {
    if (!alertsOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAlertsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [alertsOpen]);

  return { alertsOpen, alertRows, alertsLoading, openAlerts, closeAlerts };
}