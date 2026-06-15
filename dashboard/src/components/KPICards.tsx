"use client";
import { useCallback } from "react";
import { api } from "@/lib/api";
import type { DashboardSummary } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { useAsyncData } from "@/lib/useAsyncData";
import { useActiveAlerts } from "@/lib/useActiveAlerts";
import { KPICard } from "./KPICard";
import { buildKpiCards } from "@/lib/kpiCards";
import { styles } from "./KPICards.styles";

/** INR — onboarding & KPIs use Indian revenue bands (K / L). */

export default function KPICards() {
  const { period, dataVersion } = useDashboardPeriod();
  const loadSummary = useCallback(() => api.getSummary(period), [period]);
  const { data, loading } = useAsyncData<DashboardSummary>(
    `dashboard-summary:${period}:${dataVersion}`,
    loadSummary,
  );
  const { alertRows, openAlerts } = useActiveAlerts();
  const cards = buildKpiCards(data, loading);

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
      {cards.map((card) => (
        <KPICard
          key={card.label}
          card={card}
          activeAlerts={data?.active_alerts ?? 0}
          onAlertsClick={openAlerts}
        />
      ))}
    </div>
  );
}