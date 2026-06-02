"use client";
import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { api, BusinessInfo } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import type { DashboardPeriod } from "@/lib/dashboardPeriod";
import { ExportIcon } from "./Icons";

export default function WelcomeBanner() {
  const { period, setPeriod, dataVersion } = useDashboardPeriod();
  const [business, setBusiness] = useState<BusinessInfo | null>(null);
  const [exporting, setExporting] = useState(false);
  const now = new Date();
  const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const dateStr = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;

  useEffect(() => {
    api.getBusinessInfo().then(setBusiness).catch(console.error);
  }, [dataVersion]);

  useEffect(() => {
    const name = business?.user_name?.trim();
    if (!name) return;
    try {
      const raw = localStorage.getItem("profit_pilot_user");
      const u = raw ? (JSON.parse(raw) as Record<string, unknown>) : {};
      if (u.full_name === name) return;
      localStorage.setItem(
        "profit_pilot_user",
        JSON.stringify({ ...u, full_name: name }),
      );
      window.dispatchEvent(new Event("profitpilot-user"));
    } catch {
      /* ignore */
    }
  }, [business]);

  const handleExport = async () => {
    try {
      setExporting(true);
      await api.exportDashboardCsv(period);
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="welcome-banner">
      <div className="welcome-text">
        <h2>Welcome back, {business?.user_name || business?.business_name || "Guest"}!</h2>
        <p>{dateStr}</p>
      </div>
      <div className="welcome-actions">
        <div style={{ position: "relative" }}>
          <select
            className="filter-dropdown"
            style={{ appearance: "none", paddingRight: "12px" }}
            value={period}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => setPeriod(e.target.value as DashboardPeriod)}
            aria-label="Reporting period"
          >
            <option value="this_month">This Month</option>
            <option value="last_month">Last Month</option>
            <option value="ytd">Year to Date</option>
          </select>
        </div>
        <button
          type="button"
          className="export-btn"
          onClick={handleExport}
          disabled={exporting}
          aria-busy={exporting}
        >
          <ExportIcon size={14} /> {exporting ? "Exporting…" : "Export"}
        </button>
      </div>
    </div>
  );
}
