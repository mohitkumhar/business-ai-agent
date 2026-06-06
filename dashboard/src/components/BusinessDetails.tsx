"use client";
import { useEffect, useState } from "react";
import { api, BusinessInfo } from "@/lib/api";
import { useTheme } from "@/context/ThemeContext";

export default function BusinessDetails() {
  const [business, setBusiness] = useState<BusinessInfo | null>(null);
  const { theme } = useTheme();
  const isDark = theme === "dark";

  useEffect(() => {
    api.getBusinessInfo().then(setBusiness).catch(console.error);
  }, []);

  if (!business) return null;

  return (
    <div className="charts-row" style={{ gridTemplateColumns: "1fr" }}>
      <div className="chart-card" style={{ padding: "24px" }}>
        <h3 style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px", color: "var(--text-primary)" }}>
          🚀 Your Business Profile
          <span style={{ fontSize: "12px", background: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)", padding: "4px 12px", borderRadius: "100px", fontWeight: "normal", color: "var(--text-secondary)" }}>
            Data from Onboarding
          </span>
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "24px" }}>
          <DetailItem label="Business Category" value={business.industry_type || "nill"} />
          <DetailItem label="City/Location" value={business.city || "nill"} />
          <DetailItem label="Business Age" value={business.business_age || "nill"} />
          <DetailItem label="Employee count" value={business.employees_range || "nill"} />
          <DetailItem label="Biggest Challenge" value={business.biggest_challenge || "nill"} />
          <DetailItem label="Finance Tracking" value={business.finance_tracking_method || "nill"} />
        </div>
        
        {business.onboarding_notes && (
          <div style={{ marginTop: "24px", paddingTop: "20px", borderTop: `1px solid ${isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"}` }}>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px" }}>Onboarding Notes</p>
            <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--text-primary)" }}>{business.onboarding_notes || "nill"}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "4px" }}>{label}</p>
      <p style={{ fontSize: "16px", fontWeight: "600", color: "var(--text-primary)" }}>{value || "nill"}</p>
    </div>
  );
}
