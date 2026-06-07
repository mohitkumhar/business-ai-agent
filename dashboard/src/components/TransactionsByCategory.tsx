"use client";
import { useCallback, useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { api, RevenueVsExpense } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useTheme } from "@/context/ThemeContext";
import { useAsyncData } from "@/lib/useAsyncData";
import { PieChartIcon } from "./Icons";
import { LoadingSpinner } from "./LoadingStates";

Chart.register(...registerables);

export default function TransactionsByCategory() {
  // Dono branches ke hooks combine kiye
  const { period, dataVersion } = useDashboardPeriod();
  const { theme } = useTheme();
  
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const loadRevenueVsExpense = useCallback(
    () => api.getRevenueVsExpense(period),
    [period],
  );
  const { data, loading } = useAsyncData<RevenueVsExpense>(
    `transactions-by-category:${period}:${dataVersion}`,
    loadRevenueVsExpense,
  );

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.destroy();

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    // Dark mode supporting logic from kushal-dev
    const isDark = theme === "dark";
    const textColor = isDark ? "#94A3B8" : "#64748B";
    const sliceBorderColor = isDark ? "#111827" : "#FFFFFF";
    const tooltipBg = isDark ? "#1E293B" : "#0F172A";

    const colors = [
      "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
      "#EC4899", "#06B6D4", "#F97316", "#6366F1", "#14B8A6",
    ];

    chartInstance.current = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [{
          data: data.revenue,
          backgroundColor: colors.slice(0, data.labels.length),
          borderWidth: 2,
          borderColor: sliceBorderColor,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { font: { family: "Inter", size: 11 }, boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: "circle", padding: 12, color: textColor },
          },
          tooltip: {
            backgroundColor: tooltipBg,
            titleFont: { family: "Inter", size: 12 },
            bodyFont: { family: "Inter", size: 11 },
            padding: 12,
            cornerRadius: 8,
            callbacks: { label: (ctx) => `${ctx.label}: ₹${ctx.parsed.toLocaleString()}` },
          },
        },
      },
    });

    return () => { chartInstance.current?.destroy(); };
  }, [data, theme]);

  return (
    <div className="chart-card" key={dataVersion}>
      <div className="chart-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <PieChartIcon size={18} color="var(--accent-green)" />
          <span className="chart-title">Transactions by Category</span>
        </div>
      </div>
      <div className="chart-body">
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 260, width: "100%" }}>
            <LoadingSpinner label="Loading transactions…" />
          </div>
        ) : <canvas ref={chartRef}></canvas>}
      </div>
    </div>
  );
}
