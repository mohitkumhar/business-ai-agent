"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import { api, FinancialOverview } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useAsyncData } from "@/lib/useAsyncData";

Chart.register(...registerables);

function formatInrFull(n: number): string {
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
}

function formatYAxisTick(n: number): string {
  const v = Math.abs(n);
  if (v >= 100000) return `${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `${(v / 1000).toFixed(0)}k`;
  return String(Math.round(n));
}

export default function RevenueInsights() {
  const { period, dataVersion } = useDashboardPeriod();

  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const loadFinancialOverview = useCallback(
    () => api.getFinancialOverview(period),
    [period],
  );
  const { data, loading } = useAsyncData<FinancialOverview>(
    `financial-overview:${period}:${dataVersion}`,
    loadFinancialOverview,
  );
  const [view, setView] = useState<"monthly" | "yearly">("monthly");

  const chartPayload = useMemo(() => {
    if (!data) return null;
    const monthNames = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    const shortLabels = data.labels.map((l) => {
      const parts = l.split("-");
      if (parts.length >= 2) {
        const mi = parseInt(parts[1], 10);
        if (!Number.isNaN(mi) && mi >= 1 && mi <= 12) return monthNames[mi - 1];
      }
      return l;
    });

    if (view === "monthly") {
      return {
        labels: shortLabels,
        revenue: data.revenue,
        expenses: data.expenses,
      };
    }
    const rTot = data.revenue.reduce((a, b) => a + b, 0);
    const eTot = data.expenses.reduce((a, b) => a + b, 0);
    return {
      labels: ["6-month total"],
      revenue: [rTot],
      expenses: [eTot],
    };
  }, [data, view]);

  useEffect(() => {
    if (!chartPayload || !chartRef.current) return;

    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    // Create gradient fill for revenue bars
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, "rgba(59, 130, 246, 0.9)");
    gradient.addColorStop(0.5, "rgba(59, 130, 246, 0.6)");
    gradient.addColorStop(1, "rgba(59, 130, 246, 0.3)");

    chartInstance.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels: chartPayload.labels,
        datasets: [
          {
            label: "Earning",
            data: chartPayload.revenue,
            backgroundColor: gradient,
            borderColor: "rgba(59, 130, 246, 1)",
            borderWidth: 0,
            borderRadius: 6,
            borderSkipped: false,
          },
          {
            label: "Expenses",
            data: chartPayload.expenses,
            backgroundColor: "rgba(226, 232, 240, 0.8)",
            borderColor: "rgba(226, 232, 240, 1)",
            borderWidth: 0,
            borderRadius: 6,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          intersect: false,
          mode: "index",
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1E293B",
            titleFont: { family: "Inter", size: 12, weight: "bold" },
            bodyFont: { family: "Inter", size: 11 },
            padding: 14,
            cornerRadius: 10,
            displayColors: true,
            boxPadding: 6,
            callbacks: {
              label(ctx) {
                return `${ctx.dataset.label}: ₹${(ctx.parsed?.y ?? 0).toLocaleString("en-IN")}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              font: { family: "Inter", size: 11, weight: 500 },
              color: "#94A3B8",
            },
            border: { display: false },
          },
          y: {
            grid: {
              color: "rgba(0,0,0,0.04)",
            },
            ticks: {
              font: { family: "Inter", size: 11 },
              color: "#94A3B8",
              callback(value) {
                return formatYAxisTick(Number(value));
              },
            },
            border: { display: false },
          },
        },
      },
    });

    return () => {
      chartInstance.current?.destroy();
    };
  }, [chartPayload, view]);

  const sumRev = data ? data.revenue.reduce((a, b) => a + b, 0) : 0;
  const sumExp = data ? data.expenses.reduce((a, b) => a + b, 0) : 0;
  const n = data?.revenue.length || 1;
  const avgMonthlyRevenue = data ? sumRev / n : 0;
  const avgMonthlyExpense = data ? sumExp / n : 0;

  return (
    <div className="chart-card" key={dataVersion}>
      <div className="chart-header">
        <div>
          <div className="chart-title">Revenue Insights</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginTop: 4 }}>
            <span className="chart-subtitle">
              ₹{sumRev.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
            </span>

          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div className="chart-legend">
            <div className="legend-item">
              <span className="legend-dot" style={{ background: "#3B82F6" }}></span>
              Earning
            </div>
            <div className="legend-item">
              <span className="legend-dot" style={{ background: "#E2E8F0" }}></span>
              Expenses
            </div>
          </div>
          <div className="toggle-group">
            <button
              className={`toggle-btn ${view === "monthly" ? "active" : ""}`}
              onClick={() => setView("monthly")}
            >
              Monthly
            </button>
            <button
              className={`toggle-btn ${view === "yearly" ? "active" : ""}`}
              onClick={() => setView("yearly")}
            >
              Yearly
            </button>
          </div>
        </div>
      </div>
      <div className="chart-body">
        {loading ? (
          <div className="loading-spinner">Loading chart data...</div>
        ) : (
          <canvas ref={chartRef}></canvas>
        )}
      </div>
    </div>
  );
}
