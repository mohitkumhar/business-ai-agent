import React from "react";
import type { DashboardSummary } from "@/lib/api";
import type { KpiCardData } from "@/types/kpi";
import { formatCurrency, formatNumber } from "@/lib/chatUtils";
import {
  DollarIcon,
  ReceiptIcon,
  TrendingUpIcon,
  ArrowsRepeatIcon,
  AlertTriangleIcon,
} from "@/components/Icons";

/** Builds the KPI card data for the dashboard summary, or an empty list while data is unavailable. */
export function buildKpiCards(data: DashboardSummary | null, loading: boolean): KpiCardData[] {
  if (!data) return [];

  return [
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
  ];
}