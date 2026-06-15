export interface ActiveAlertRow {
  alert_id: number;
  severity: "Low" | "Medium" | "High";
  message: string;
  created_at: string;
}
import type { ReactNode } from "react";

export interface KpiCardData {
  label: string;
  value: string;
  change: string;
  positive: boolean;
  icon: ReactNode;
  accentColor: string;
  iconBg: string;
  iconColor: string;
}