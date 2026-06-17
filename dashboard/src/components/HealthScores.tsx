"use client";
import { useEffect, useState } from "react";
import { api, HealthScores as HealthScoresData } from "@/lib/api";
import { HeartPulseIcon } from "./Icons";
import { useTheme } from "@/context/ThemeContext";

function getScoreColor(score: number): string {
  if (score >= 75) return "#10B981"; // Excellent
  if (score >= 60) return "#F59E0B"; // Good
  return "#EF4444"; // At Risk
}

function getScoreBg(score: number, isDark: boolean): string {
  if (isDark) {
    if (score >= 75) return "rgba(16, 185, 129, 0.15)";
    if (score >= 60) return "rgba(245, 158, 11, 0.15)";
    return "rgba(239, 68, 68, 0.15)";
  }
  if (score >= 75) return "#ECFDF5";
  if (score >= 60) return "#FFFBEB";
  return "#FEF2F2";
}

export default function HealthScores() {
  const [data, setData] = useState<HealthScoresData | null>(null);
  const [loading, setLoading] = useState(true);
  const { theme } = useTheme();
  const isDark = theme === "dark";

  useEffect(() => {
    api.getHealthScores()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="chart-card h-full flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" 
             style={{ background: isDark ? "rgba(239, 68, 68, 0.15)" : "#FEF2F2" }}>
          <HeartPulseIcon size={18} color="#EF4444" />
        </div>
        <h3 className="text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
          Business Health Scores
        </h3>
      </div>

      <div className="flex-1">
        {loading ? (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: "var(--text-muted)" }}>
            Calculating scores...
          </div>
        ) : data && data.scores.length > 0 ? (
          <div className="space-y-6">
            {data.scores.map((biz) => (
              <div key={biz.name} className="p-5 rounded-2xl" 
                   style={{ 
                     border: "1px solid var(--border-color)", 
                     background: isDark ? "rgba(255,255,255,0.02)" : "rgba(15, 23, 42, 0.02)" 
                   }}>
                <div className="flex justify-between items-center mb-5">
                  <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{biz.name}</span>
                  <div className="px-3 py-1.5 rounded-full text-sm font-bold transition-all shadow-sm"
                    style={{
                      color: getScoreColor(biz.overall),
                      background: isDark ? "rgba(255,255,255,0.05)" : "white",
                      border: `1px solid ${getScoreBg(biz.overall, isDark)}`
                    }}>
                    {biz.overall}
                  </div>
                </div>

                <div className="grid grid-cols-5 gap-4">
                  {[
                    { label: "Cash", value: biz.cash },
                    { label: "Profit", value: biz.profitability },
                    { label: "Growth", value: biz.growth },
                    { label: "Cost", value: biz.cost_control },
                    { label: "Risk", value: biz.risk },
                  ].map((metric) => (
                    <div key={metric.label} className="text-center group">
                      <div className="text-[10px] font-bold mb-2 uppercase tracking-wider"
                           style={{ color: "var(--text-secondary)" }}>
                        {metric.label}
                      </div>
                      <div className="w-full h-1.5 rounded-full overflow-hidden mb-2 relative"
                           style={{ background: isDark ? "#1E293B" : "#E2E8F0" }}>
                        <div
                          className="h-full rounded-full transition-all duration-1000 ease-out"
                          style={{
                            width: `${metric.value}%`,
                            background: getScoreColor(metric.value),
                          }}
                        />
                      </div>
                      <div className="text-xs font-bold" style={{ color: "var(--text-primary)" }}>
                        {metric.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-sm italic" style={{ color: "var(--text-muted)" }}>
            No health data available
          </div>
        )}
      </div>
    </div>
  );
}
