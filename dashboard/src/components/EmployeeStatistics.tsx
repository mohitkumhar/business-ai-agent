"use client";
import { useEffect, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import { api, EmployeeStats as EmployeeStatsData } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useTheme } from "@/context/ThemeContext";
import { UsersIcon } from "./Icons";
import { LoadingSpinner } from "./LoadingStates";

Chart.register(...registerables);

export default function EmployeeStatistics() {
  const { dataVersion } = useDashboardPeriod();
  const { theme } = useTheme();
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const [data, setData] = useState<EmployeeStatsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getEmployeeStats()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [dataVersion]);

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.destroy();

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    const isDark = theme === "dark";
    const textColor = isDark ? "#94A3B8" : "#64748B";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.05)" : "rgba(0, 0, 0, 0.04)";
    const tooltipBg = isDark ? "#1E293B" : "#0F172A";

    chartInstance.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Employee Count",
            data: data.counts,
            backgroundColor: "rgba(99, 102, 241, 0.75)",
            borderRadius: 4,
            borderSkipped: false,
            yAxisID: "y",
          },
          {
            label: "Avg Salary ($)",
            data: data.avg_salary,
            type: "line",
            borderColor: "#F59E0B",
            backgroundColor: "rgba(245, 158, 11, 0.1)",
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: "#F59E0B",
            pointBorderColor: "#FFFFFF",
            pointBorderWidth: 2,
            borderWidth: 2,
            yAxisID: "y1",
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
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 10 }, color: textColor, maxRotation: 45 }, border: { display: false } },
          y: {
            position: "left",
            grid: { color: gridColor },
            ticks: { font: { family: "Inter", size: 11 }, color: textColor },
            border: { display: false },
            title: { display: true, text: "Count", font: { family: "Inter", size: 11 }, color: textColor },
          },
          y1: {
            position: "right",
            grid: { display: false },
            ticks: { font: { family: "Inter", size: 11 }, color: textColor, callback(v) { const n = Number(v); return n >= 1000 ? `${(n / 1000).toFixed(0)}k` : String(v); } },
            border: { display: false },
            title: { display: true, text: "Salary ($)", font: { family: "Inter", size: 11 }, color: textColor },
          },
        },
      },
    });

    return () => { chartInstance.current?.destroy(); };
  }, [data, theme]);

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <UsersIcon size={18} color="var(--accent-purple)" />
          <span className="chart-title">Employee Statistics</span>
        </div>
      </div>
      <div className="chart-body">
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 260, width: "100%" }}>
            <LoadingSpinner label="Loading employee data…" />
          </div>
        ) : <canvas ref={chartRef}></canvas>}
      </div>
    </div>
  );
}
