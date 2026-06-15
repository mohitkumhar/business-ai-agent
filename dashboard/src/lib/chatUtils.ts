export function friendlyNodeName(node: string): string {
  return node.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
export function formatCurrency(value: number): string {
  const v = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (v >= 1e7) return `${sign}₹${(v / 1e7).toFixed(2)} Cr`;
  if (v >= 1e5) return `${sign}₹${(v / 1e5).toFixed(2)} L`;
  if (v >= 1e3) return `${sign}₹${(v / 1e3).toFixed(1)} K`;
  return `${sign}₹${Math.round(v).toLocaleString("en-IN")}`;
}

export function formatNumber(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
}

export function formatPct(pct: number | null | undefined): string {
  if (pct == null || Number.isNaN(pct)) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function severityBadgeLabel(sev: string | null | undefined): string {
  if (!sev) return "Active";
  if (sev === "High") return "Critical";
  if (sev === "Medium") return "Medium";
  if (sev === "Low") return "Low";
  return sev;
}