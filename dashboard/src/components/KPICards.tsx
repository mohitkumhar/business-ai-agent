"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { DashboardSummary, Alert } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useAsyncData } from "@/lib/useAsyncData";
import {
  DollarIcon,
  ReceiptIcon,
  TrendingUpIcon,
  ArrowsRepeatIcon,
  AlertTriangleIcon,
  InfoIcon,
} from "./Icons";

interface ActiveAlertRow {
  alert_id: number;
  severity: "Low" | "Medium" | "High";
  message: string;
  created_at: string;
}


/** INR — onboarding & KPIs use Indian revenue bands (K / L). */
function formatCurrency(value: number): string {
  const v = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (v >= 1e7) return `${sign}₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `${sign}₹${(v / 1e5).toFixed(2)} L`;
  if (v >= 1e3) return `${sign}₹${(v / 1e3).toFixed(1)} K`;
  return `${sign}₹${Math.round(v).toLocaleString("en-IN")}`;
}

function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

function formatPct(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

function severityBadgeLabel(sev: string | null | undefined): string {
  if (!sev) return "Active";
  if (sev === "High") return "Critical";
  if (sev === "Medium") return "Medium";
  if (sev === "Low") return "Low";
  return sev;
}

export default function KPICards() {
  const { period, dataVersion } = useDashboardPeriod();
  const loadSummary = useCallback(() => api.getSummary(period), [period]);
  const { data, loading } = useAsyncData<DashboardSummary>(
    `dashboard-summary:${period}:${dataVersion}`,
    loadSummary,
  );
  const [alertsOpen, setAlertsOpen] = useState(false);
  const [alertRows, setAlertRows] = useState<Alert[]>([]);
  const [alertsStatus, setAlertsStatus] = useState<"idle" | "loading" | "loaded">("idle");
  const alertsLoading = alertsStatus === "loading";

  const openAlerts = () => {
    setAlertsStatus("loading");
    setAlertsOpen(true);
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

  const cards = data
    ? [
      {
        label: "Total Revenue",
        value: loading ? "..." : `$${(data?.total_revenue || 0).toLocaleString()}`,
        change: loading ? "0%" : `${(data?.revenue_change || 0)}%`,
        positive: !loading && (data?.revenue_change ?? 0) >= 0,
        icon: <DollarIcon size={18} />,
        accentColor: "#3B82F6",
        iconBg: "rgba(59, 130, 246, 0.1)",
        iconColor: "#3B82F6",
      },
      {
        label: "Total Expenses",
        value: loading ? "..." : `$${(data?.total_expenses || 0).toLocaleString()}`,
        change: loading ? "0%" : `${(data?.expenses_change || 0)}%`,
        positive: !loading && (data?.expenses_change ?? 0) < 0,
        icon: <ReceiptIcon size={18} />,
        accentColor: "#EF4444",
        iconBg: "rgba(239, 68, 68, 0.1)",
        iconColor: "#EF4444",
      },
      {
        label: "Net Profit",
        value: formatCurrency(data.net_profit || 0),
        change: loading ? "0%" : `${(data?.net_profit_change || 0)}%`,
        positive: !loading && (data?.net_profit_change ?? 0) >= 0,
        icon: <TrendingUpIcon size={18} />,
        iconBg: "#F0FDF4",
        iconColor: "#16A34A",
        accentColor: "#16A34A",
      },
      {
        label: "Transactions",
        value: formatNumber(data.total_transactions || 0),
        change: loading ? "0%" : `${(data?.transactions_change || 0)}%`,
        positive: !loading && (data?.transactions_change ?? 0) >= 0,
        icon: <ArrowsRepeatIcon size={18} />,
        iconBg: "#FFFBEB",
        iconColor: "#D97706",
        accentColor: "#D97706",
      },
      {
        label: "Active Alerts",
        value: formatNumber(data.active_alerts || 0),
        change: "",
        positive: false,
        icon: <AlertTriangleIcon size={18} />,
        iconBg: "#FEF2F2",
        iconColor: "#DC2626",
        accentColor: "#DC2626",
      },
    ]
    : [];

  if (loading) {
    return (
      <div style={styles.grid}>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} style={styles.card}>
            <div style={{ ...styles.skeleton, width: 40, height: 40, borderRadius: 10, marginBottom: 12 }} />
            <div style={{ ...styles.skeleton, width: "60%", height: 13, marginBottom: 10 }} />
            <div style={{ ...styles.skeleton, width: "45%", height: 28, marginBottom: 10 }} />
            <div style={{ ...styles.skeleton, width: "80%", height: 11 }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div style={styles.grid}>
      {cards.map((card) => {
        const clickable = card.label === "Active Alerts";
        const cardContent = (
          <div
            style={styles.card}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
              (e.currentTarget as HTMLDivElement).style.boxShadow =
                "0 8px 24px rgba(0,0,0,0.08)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
              (e.currentTarget as HTMLDivElement).style.boxShadow =
                "0 1px 4px rgba(0,0,0,0.04)";
            }}
          >
            {/* Top accent line */}
            <div
              key={card.label}
              role={card.label === "Active Alerts" ? "button" : undefined}
              tabIndex={card.label === "Active Alerts" ? 0 : undefined}
              onClick={() => {
                if (card.label === "Active Alerts") openAlerts();
              }}
              onKeyDown={(e) => {
                if (card.label === "Active Alerts" && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  openAlerts();
                }
              }}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                height: "3px",
                background: card.accentColor,
                borderRadius: "12px 12px 0 0",
                opacity: 0.7,
              }}
            />

            {/* Header row: icon + label + info */}
            <div style={styles.headerRow}>
              <div
                style={{
                  ...styles.iconBox,
                  background: card.iconBg,
                  color: card.iconColor,
                }}
              >
                {card.icon}
              </div>
              <div style={styles.labelGroup}>
                <span style={styles.label}>{card.label}</span>
                <span style={{ color: "#9CA3AF", cursor: "pointer" }} title={`${card.label} info`}>
                  <InfoIcon size={13} />
                </span>
              </div>
            </div>

            {/* Big Value */}
            <div style={styles.value}>{card.value}</div>

            {/* Badge */}
            {card.label === "Active Alerts" ? (
              <div
                style={{
                  ...styles.badge,
                  background: (data?.active_alerts ?? 0) > 0 ? "#FEF2F2" : "#F0FDF4",
                  color: (data?.active_alerts ?? 0) > 0 ? "#DC2626" : "#16A34A",
                }}
              >
                <span style={{ fontSize: 11, fontWeight: 600 }}>
                  {(data?.active_alerts ?? 0) > 0 ? "Critical" : "All Clear"}
                </span>
              </div>

            ) : (
              <div
                style={{
                  ...styles.badge,
                  background: card.positive ? "#F0FDF4" : "#FEF2F2",
                  color: card.positive ? "#16A34A" : "#DC2626",
                }}
              >
                <span style={{ fontSize: 12 }}>{card.positive ? "↑" : "↓"}</span>
                <span style={{ fontSize: 12, fontWeight: 600 }}>{card.change}</span>
              </div>
            )}
          </div>
        );

        return card.label === "Active Alerts" ? (
          <Link key={card.label} href="/alerts" style={{ textDecoration: "none" }}>
            {cardContent}
          </Link>
        ) : (
          <div key={card.label}>{cardContent}</div>
        );
      })}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "16px",
    width: "100%",
    marginBottom: "40px",
  },
  card: {
    position: "relative",
    background: "var(--kpi-card-bg)",
    borderRadius: "12px",
    border: "1px solid var(--kpi-card-border)",
    boxShadow: "var(--shadow-card)",
    padding: "20px 18px 16px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
    transition: "transform 0.2s ease, box-shadow 0.2s ease, background-color 0.3s ease, border-color 0.3s ease",
    cursor: "default",
    overflow: "hidden",
  },
  headerRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    marginBottom: "6px",
  },
  iconBox: {
    width: "36px",
    height: "36px",
    borderRadius: "9px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  labelGroup: {
    display: "flex",
    alignItems: "center",
    gap: "5px",
  },
  label: {
    fontSize: "13px",
    color: "var(--kpi-label-color)",
    fontWeight: 500,
    whiteSpace: "nowrap",
  },
  value: {
    fontSize: "26px",
    fontWeight: 700,
    color: "var(--kpi-value-color)",
    letterSpacing: "-0.5px",
    lineHeight: 1.2,
    margin: "4px 0",
  },
  badge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "3px",
    padding: "4px 8px",
    borderRadius: "6px",
    width: "fit-content",
    marginTop: "4px",
  },
  skeleton: {
    background: "linear-gradient(90deg, var(--skeleton-from) 25%, var(--skeleton-mid) 50%, var(--skeleton-to) 75%)",
    backgroundSize: "200% 100%",
    animation: "shimmer 1.5s infinite",
    borderRadius: "6px",
  },
  modalBackdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(15, 23, 42, 0.45)",
    zIndex: 1000,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  modalPanel: {
    background: "#fff",
    borderRadius: 16,
    maxWidth: 480,
    width: "100%",
    maxHeight: "min(80vh, 520px)",
    overflow: "auto",
    padding: "20px 22px",
    boxShadow: "0 25px 50px rgba(0,0,0,0.15)",
  },
  modalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  modalTitle: {
    margin: 0,
    fontSize: 18,
    fontWeight: 700,
    color: "#0F172A",
  },
  modalClose: {
    border: "none",
    background: "transparent",
    fontSize: 24,
    lineHeight: 1,
    cursor: "pointer",
    color: "#64748B",
    padding: "0 4px",
  },
  alertList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  alertItem: {
    border: "1px solid #E2E8F0",
    borderRadius: 10,
    padding: "12px 14px",
  },
  alertTop: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
    flexWrap: "wrap",
  },
  sevPill: {
    fontSize: 11,
    fontWeight: 700,
    padding: "2px 8px",
    borderRadius: 6,
  },
  alertMessage: {
    margin: 0,
    fontSize: 14,
    color: "#1E293B",
    lineHeight: 1.45,
  },
  alertMeta: {
    margin: "8px 0 0",
    fontSize: 11,
    color: "#94A3B8",
  },
};
