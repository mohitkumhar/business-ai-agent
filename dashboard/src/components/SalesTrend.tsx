"use client";
import { useCallback, useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { api, SalesTrend as SalesTrendData } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useTheme } from "@/context/ThemeContext";
import { useAsyncData } from "@/lib/useAsyncData";
import { LineChartIcon } from "./Icons";
import { LoadingSpinner } from "./LoadingStates";

Chart.register(...registerables);

export default function SalesTrend() {
  const { period, dataVersion } = useDashboardPeriod();

  const { theme } = useTheme();
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const loadSalesTrend = useCallback(
    () => api.getSalesTrend(period),
    [period],
  );
  const { data, loading } = useAsyncData<SalesTrendData>(
    `sales-trend:${period}:${dataVersion}`,
    loadSalesTrend,
  );

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.destroy();

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    const isDark = theme === "dark";
    const textColor = isDark ? "#94A3B8" : "#64748B";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.04)";
    const tooltipBg = isDark ? "#1E293B" : "#0F172A";
    const pointBorder = isDark ? "#111827" : "#FFFFFF";

    const gradient = ctx.createLinearGradient(0, 0, 0, 260);
    gradient.addColorStop(0, "rgba(59, 130, 246, 0.25)");
    gradient.addColorStop(1, "rgba(59, 130, 246, 0.02)");

    chartInstance.current = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Revenue",
            data: data.revenue,
            borderColor: "#3B82F6",
            backgroundColor: gradient,
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: "#3B82F6",
            pointBorderColor: pointBorder,
            pointBorderWidth: 2,
            borderWidth: 2.5,
          },
          {
            label: "Expenses",
            data: data.expenses,
            borderColor: "#EF4444",
            backgroundColor: "transparent",
            fill: false,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: "#EF4444",
            pointBorderColor: pointBorder,
            pointBorderWidth: 2,
            borderWidth: 2,
            borderDash: [5, 5],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            align: "end",
            labels: { font: { family: "Inter", size: 11 }, boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: "circle", padding: 16, color: textColor },
          },
          tooltip: {
            backgroundColor: tooltipBg,
            titleFont: { family: "Inter", size: 12 },
            bodyFont: { family: "Inter", size: 11 },
            padding: 12,
            cornerRadius: 8,
            callbacks: { label: (ctx) => `${ctx.dataset.label}: $${(ctx.parsed?.y ?? 0).toLocaleString()}` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 }, color: textColor }, border: { display: false } },
          y: { grid: { color: gridColor }, ticks: { font: { family: "Inter", size: 11 }, color: textColor, callback(v) { const n = Number(v); return n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(v); } }, border: { display: false } },
        },
      },
    });

    return () => { chartInstance.current?.destroy(); };
  }, [data, theme]);

  return (
    <div className="chart-card" key={dataVersion}>
      <div className="chart-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <LineChartIcon size={18} color="var(--accent-blue)" />
          <span className="chart-title">Sales Trend (Last 7 Days)</span>
        </div>
      </div>
      <div className="chart-body">
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 260, width: "100%" }}>
            <LoadingSpinner label="Loading sales data…" />
          </div>
        ) : <canvas ref={chartRef}></canvas>}
      </div>
    </div>
  );
}
