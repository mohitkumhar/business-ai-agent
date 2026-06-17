"use client";
import { useCallback, useEffect, useRef } from "react";
import { Chart, registerables } from "chart.js";
import { api, AlertsBySeverity as AlertsData } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useAsyncData } from "@/lib/useAsyncData";
import { AlertTriangleIcon } from "./Icons";

Chart.register(...registerables);

export default function AlertsBySeverity() {
  const { period, dataVersion } = useDashboardPeriod();
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const loadAlertsBySeverity = useCallback(
    () => api.getAlertsBySeverity(period),
    [period],
  );
  const { data, loading } = useAsyncData<AlertsData>(
    `alerts-by-severity:${period}:${dataVersion}`,
    loadAlertsBySeverity,
  );

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.destroy();

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    const colorMap: Record<string, string> = {
      critical: "#EF4444",
      high: "#F97316",
      medium: "#F59E0B",
      low: "#10B981",
      info: "#3B82F6",
    };

    const colors = data.labels.map((l) => colorMap[l.toLowerCase()] || "#94A3B8");

    chartInstance.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Alerts",
          data: data.data,
          backgroundColor: colors,
          borderRadius: 6,
          borderSkipped: false,
          maxBarThickness: 40,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1E293B",
            titleFont: { family: "Inter", size: 12 },
            bodyFont: { family: "Inter", size: 11 },
            padding: 12,
            cornerRadius: 8,
          },
        },
        scales: {
          x: { grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { family: "Inter", size: 11 }, color: "#94A3B8" }, border: { display: false } },
          y: { grid: { display: false }, ticks: { font: { family: "Inter", size: 12, weight: 500 as const }, color: "#1E293B" }, border: { display: false } },
        },
      },
    });

    return () => { chartInstance.current?.destroy(); };
  }, [data]);

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <AlertTriangleIcon size={18} color="#F59E0B" />
          <span className="chart-title">Alerts by Severity</span>
        </div>
      </div>
      <div className="chart-body">
        {loading ? <div className="loading-spinner">Loading...</div> : <canvas ref={chartRef}></canvas>}
      </div>
    </div>
  );
}
