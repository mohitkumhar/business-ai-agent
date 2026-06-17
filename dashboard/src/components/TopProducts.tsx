"use client";
import { useEffect, useRef, useState } from "react";
import { Chart, registerables } from "chart.js";
import { api, TopProducts as TopProductsData } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { PackageIcon } from "./Icons";

Chart.register(...registerables);

export default function TopProducts() {
  const { dataVersion } = useDashboardPeriod();
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);
  const [data, setData] = useState<TopProductsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTopProducts()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [dataVersion]);

  useEffect(() => {
    if (!data || !chartRef.current) return;
    if (chartInstance.current) chartInstance.current.destroy();

    const ctx = chartRef.current.getContext("2d");
    if (!ctx) return;

    chartInstance.current = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Stock",
            data: data.stock,
            backgroundColor: "rgba(59, 130, 246, 0.75)",
            borderRadius: 4,
            borderSkipped: false,
          },
          {
            label: "Margin %",
            data: data.margin_pct ?? data.margin,
            backgroundColor: "rgba(16, 185, 129, 0.75)",
            borderRadius: 4,
            borderSkipped: false,
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
            labels: { font: { family: "Inter", size: 11 }, boxWidth: 8, boxHeight: 8, usePointStyle: true, pointStyle: "circle", padding: 16, color: "#64748B" },
          },
          tooltip: {
            backgroundColor: "#1E293B",
            titleFont: { family: "Inter", size: 12 },
            bodyFont: { family: "Inter", size: 11 },
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: (context) => {
                const value = Number(context.parsed.y ?? 0);
                return context.dataset.label === "Margin %" ? `Margin: ${value.toFixed(1)}%` : `Stock: ${value}`;
              },
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 10 }, color: "#94A3B8", maxRotation: 45 }, border: { display: false } },
          y: { grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { family: "Inter", size: 11 }, color: "#94A3B8" }, border: { display: false } },
        },
      },
    });

    return () => { chartInstance.current?.destroy(); };
  }, [data]);

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <PackageIcon size={18} color="var(--accent-blue)" />
          <span className="chart-title">Top Products by Stock</span>
        </div>
      </div>
      <div className="chart-body">
        {loading ? <div className="loading-spinner">Loading...</div> : <canvas ref={chartRef}></canvas>}
      </div>
    </div>
  );
}
