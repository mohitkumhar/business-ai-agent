"use client";
import { useCallback } from "react";
import { api, SalesTarget } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useTheme } from "@/context/ThemeContext";
import { useAsyncData } from "@/lib/useAsyncData";
import { LoadingSpinner } from "./LoadingStates";

function SemiCircleGauge({ percentage, isDark }: { percentage: number; isDark: boolean }) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2 + 10;
  const r = 75;
  const total = 12;
  const startAngle = -180;
  const endAngle = 0;
  const filledCount = Math.round((percentage / 100) * total);

  const segments = Array.from({ length: total }, (_, i) => {
    const angleStep = 180 / (total - 1);
    const angle = startAngle + i * angleStep;
    const rad = (angle * Math.PI) / 180;
    const innerR = r - 14;
    const outerR = r + 2;
    const gapAngle = 4;
    const startRad = ((angle - angleStep / 2 + gapAngle / 2) * Math.PI) / 180;
    const endRad = ((angle + angleStep / 2 - gapAngle / 2) * Math.PI) / 180;

    const x1 = cx + innerR * Math.cos(startRad);
    const y1 = cy + innerR * Math.sin(startRad);
    const x2 = cx + outerR * Math.cos(startRad);
    const y2 = cy + outerR * Math.sin(startRad);
    const x3 = cx + outerR * Math.cos(endRad);
    const y3 = cy + outerR * Math.sin(endRad);
    const x4 = cx + innerR * Math.cos(endRad);
    const y4 = cy + innerR * Math.sin(endRad);

    const isFilled = i < filledCount;
    // Multi-color blue gradient: Dark blue -> Medium blue -> Unfilled
    const fillColor = isFilled
      ? i < total * 0.4
        ? "#1D4ED8" // Dark blue
        : "#3B82F6" // Medium blue
      : isDark ? "#1E293B" : "#DBEAFE"; // Unfilled state depends on theme

    return (
      <path
        key={i}
        d={`M ${x1} ${y1} L ${x2} ${y2} A ${outerR} ${outerR} 0 0 1 ${x3} ${y3} L ${x4} ${y4} A ${innerR} ${innerR} 0 0 0 ${x1} ${y1} Z`}
        fill={fillColor}
        className="transition-all duration-700 ease-out"
        style={{ transitionDelay: `${i * 50}ms` }}
      />
    );
  });

  return (
    <div className="relative flex flex-col items-center">
      <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 20}`}>
        {segments}
        <text
          x={cx}
          y={cy - 10}
          textAnchor="middle"
          fontSize="24"
          fontWeight="700"
          fill={isDark ? "#FFFFFF" : "#0F172A"}
          style={{ fontFamily: 'Inter, sans-serif' }}
        >
          {percentage.toFixed(1)}%
        </text>
        <text
          x={cx}
          y={cy + 12}
          textAnchor="middle"
          fontSize="11"
          fontWeight="500"
          fill={isDark ? "#A1A1AA" : "#64748B"}
          style={{ fontFamily: 'Inter, sans-serif' }}
        >
          Sales Growth
        </text>
      </svg>
    </div>
  );
}

export default function SalesOverview() {
  const { period, dataVersion } = useDashboardPeriod();

  const { theme } = useTheme();
  const isDark = theme === "dark";
  const loadSalesTarget = useCallback(
  () => api.getSalesTarget(period),
  [period],
);

const { data, loading } = useAsyncData<SalesTarget>(
  `sales-overview:${period}:${dataVersion}`,
  loadSalesTarget,
);
  const sales = data?.current_revenue ?? 0;
  const target = data?.target_revenue ?? 0;
  const percentage = data?.percentage ?? 0;
  const progressPercent = Math.min((sales / target) * 100, 100);

  return (
    <div className="chart-card flex flex-col h-full" key={dataVersion}>
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>Sales Overview</h3>
        <button className="transition-colors" style={{ color: "var(--text-muted)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="1"></circle>
            <circle cx="19" cy="12" r="1"></circle>
            <circle cx="5" cy="12" r="1"></circle>
          </svg>
        </button>
      </div>

      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flex: 1, padding: "40px 0", width: "100%" }}>
          <LoadingSpinner label="Loading sales metrics…" />
        </div>
      ) : (
        <div className="flex flex-col flex-1">
          {/* Gauge Section */}
          <div className="flex-1 flex items-center justify-center py-4">
            <SemiCircleGauge percentage={percentage} isDark={isDark} />
          </div>

          {/* Bottom Section */}
          <div className="mt-auto">
            <div className="my-4" style={{ borderTop: "1px solid var(--border-color)" }}></div>
            
            <div className="flex justify-between items-end mb-3">
              <div>
                <div className="text-[11px] font-medium mb-0.5" style={{ color: "var(--text-secondary)" }}>Sales</div>
                <div className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                  ${sales.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[11px] font-medium mb-0.5" style={{ color: "var(--text-secondary)" }}>Target</div>
                <div className="text-base font-bold" style={{ color: "var(--text-primary)" }}>
                  ${target.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "var(--progress-bg)" }}>
              <div 
                className="h-full bg-blue-600 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
