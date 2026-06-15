"use client";
import Link from "next/link";
import type { KpiCardData } from "@/types/kpi";
import { InfoIcon } from "./Icons";
import { styles } from "./KPICards.styles";

interface KPICardProps {
  card: KpiCardData;
  activeAlerts: number;
  onAlertsClick: () => void;
}

/** Renders a single KPI summary card, with special handling for the "Active Alerts" card. */
export function KPICard({ card, activeAlerts, onAlertsClick }: KPICardProps) {
  const isAlertsCard = card.label === "Active Alerts";

  const cardContent = (
    <div
      style={styles.card}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          "0 8px 24px rgba(0,0,0,0.08)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
        (e.currentTarget as HTMLDivElement).style.boxShadow =
          "0 1px 4px rgba(0,0,0,0.04)";
      }}
    >
      {/* Top accent line */}
      <div
        role={isAlertsCard ? "button" : undefined}
        tabIndex={isAlertsCard ? 0 : undefined}
        onClick={() => {
          if (isAlertsCard) onAlertsClick();
        }}
        onKeyDown={(e) => {
          if (isAlertsCard && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            onAlertsClick();
          }
        }}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "3px",
          background: card.accentColor,
          borderRadius: "12px 12px 0 0",
          opacity: 0.7,
        }}
      />

      {/* Header row: icon + label + info */}
      <div style={styles.headerRow}>
        <div
          style={{
            ...styles.iconBox,
            background: card.iconBg,
            color: card.iconColor,
          }}
        >
          {card.icon}
        </div>
        <div style={styles.labelGroup}>
          <span style={styles.label}>{card.label}</span>
          <span style={{ color: "#9CA3AF", cursor: "pointer" }} title={`${card.label} info`}>
            <InfoIcon size={13} />
          </span>
        </div>
      </div>

      {/* Big Value */}
      <div style={styles.value}>{card.value}</div>

      {/* Badge */}
      {isAlertsCard ? (
        <div
          style={{
            ...styles.badge,
            background: activeAlerts > 0 ? "#FEF2F2" : "#F0FDF4",
            color: activeAlerts > 0 ? "#DC2626" : "#16A34A",
          }}
        >
          <span style={{ fontSize: 11, fontWeight: 600 }}>
            {activeAlerts > 0 ? "Critical" : "All Clear"}
          </span>
        </div>
      ) : (
        <div
          style={{
            ...styles.badge,
            background: card.positive ? "#F0FDF4" : "#FEF2F2",
            color: card.positive ? "#16A34A" : "#DC2626",
          }}
        >
          <span style={{ fontSize: 12 }}>{card.positive ? "↑" : "↓"}</span>
          <span style={{ fontSize: 12, fontWeight: 600 }}>{card.change}</span>
        </div>
      )}
    </div>
  );

  return isAlertsCard ? (
    <Link href="/alerts" style={{ textDecoration: "none" }}>
      {cardContent}
    </Link>
  ) : (
    <div>{cardContent}</div>
  );
}