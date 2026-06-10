"use client";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  fullPage?: boolean;
}

const sizeMap = {
  sm: 16,
  md: 24,
  lg: 40,
};

export function LoadingSpinner({ size = "md", label, fullPage = false }: LoadingSpinnerProps) {
  const px = sizeMap[size];
  const spinner = (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
      <svg
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        style={{ animation: "spin 1s linear infinite" }}
      >
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="var(--accent-blue, #3B82F6)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray="31.4 31.4"
          strokeDashoffset="10"
        />
      </svg>
      {label && <span style={{ fontSize: 13, color: "var(--text-muted, #64748B)" }}>{label}</span>}
    </div>
  );

  if (fullPage) {
    return (
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: 200,
        width: "100%",
      }}>
        {spinner}
      </div>
    );
  }

  return spinner;
}

export function LoadingSkeleton({ lines = 3, height = 16 }: { lines?: number; height?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, width: "100%", padding: 8 }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            height,
            background: "linear-gradient(90deg, var(--skeleton-from, #f0f0f0) 25%, var(--skeleton-mid, #e0e0e0) 50%, var(--skeleton-to, #f0f0f0) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s infinite",
            borderRadius: 6,
          }}
        />
      ))}
      <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
    </div>
  );
}

export function SkeletonCard({ lines = 4 }: { lines?: number }) {
  return (
    <div style={{
      background: "var(--kpi-card-bg, white)",
      borderRadius: 12,
      border: "1px solid var(--kpi-card-border, #e5e7eb)",
      padding: 20,
    }}>
      <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <div style={{ width: 36, height: 36, borderRadius: 9, background: "var(--skeleton-from, #f0f0f0)", animation: "shimmer 1.5s infinite", backgroundSize: "200% 100%" }} />
        <div style={{ width: "50%", height: 13, marginTop: 8, background: "var(--skeleton-from, #f0f0f0)", animation: "shimmer 1.5s infinite", backgroundSize: "200% 100%", borderRadius: 4 }} />
      </div>
      <LoadingSkeleton lines={lines} height={20} />
      <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
    </div>
  );
}