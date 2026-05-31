"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { DragEvent } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { BarChartIcon, CameraIcon, ReceiptIcon } from "@/components/Icons";
import { AGENT_API_BASE } from "@/lib/publicUrls";
import { dispatchDashboardRefresh } from "@/lib/dashboardRefresh";

function getUserEmail(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const u = JSON.parse(localStorage.getItem("profit_pilot_user") || "{}") as {
      email?: string;
    };
    return u.email?.trim() || null;
  } catch {
    return null;
  }
}

type TabId = "excel" | "accounting" | "manual" | "none";

type PreviewRow = {
  date?: string;
  type?: string;
  category?: string;
  amount?: string | number;
  description?: string;
};

export default function ImportPage() {
  const [activeTab, setActiveTab] = useState<TabId>("manual");
  const [flash, setFlash] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewRow[] | null>(null);
  const [previewHash, setPreviewHash] = useState<string | null>(null);
  const router = useRouter();

  const excelRef = useRef<HTMLInputElement>(null);
  const exportRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);

  const postSpreadsheet = async (file: File, source: string) => {
    const email = getUserEmail() || "demo@profitpilot.ai";
    const token = localStorage.getItem("profit_pilot_token");
    const headers = token ? { "Authorization": `Bearer ${token}` } : {};
    setUploading(true);
    setFlash(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("email", email);
    fd.append("source", source);
    try {
      const res = await fetch(`${AGENT_API_BASE}/api/v1/import/transactions`, {
        method: "POST",
        headers: headers as HeadersInit,
        body: fd,
      });
      const data = await res.json();

      setFlash({
        kind: res.ok ? "success" : "error",
        text: data.message || (res.ok ? "Imported successfully!" : data.error || "Failed."),
      });

      dispatchDashboardRefresh();
      if (res.ok) setTimeout(() => router.push("/"), 1500);
    } catch {
      setFlash({ kind: "error", text: "Connection error to server." });
    } finally {
      setUploading(false);
    }
  };

  const postNotebook = async (file: File) => {
    const email = getUserEmail() || "demo@profitpilot.ai";
    const token = localStorage.getItem("profit_pilot_token");
    const headers = token ? { "Authorization": `Bearer ${token}` } : ({} as HeadersInit);
    setUploading(true);
    setFlash(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("email", email);
    try {
      const res = await fetch(`${AGENT_API_BASE}/api/v1/import/notebook`, {
        method: "POST",
        headers,
        body: fd,
      });
      const data = await res.json();

      if (res.ok) {
        setPreviewData(data.transactions);
        setPreviewHash(data.hash);
        setFlash({ kind: "success", text: "Handwriting extracted! Please review below." });
      } else {
        setFlash({ kind: "error", text: data.error || "Processing failed." });
      }
    } catch {
      setFlash({ kind: "error", text: "Extraction service unavailable." });
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmNotebook = async () => {
    if (!previewData || !previewHash) return;
    const token = localStorage.getItem("profit_pilot_token");
    setUploading(true);
    try {
      const res = await fetch(`${AGENT_API_BASE}/api/v1/import/confirm-notebook`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ transactions: previewData, hash: previewHash }),
      });
      const resData = await res.json();
      if (res.ok) {
        setFlash({ kind: "success", text: resData.message || "Saved successfully!" });
        dispatchDashboardRefresh();
        setTimeout(() => router.push("/"), 2000);
      } else {
        setFlash({ kind: "error", text: resData.error || "Failed to save." });
      }
    } catch {
      setFlash({ kind: "error", text: "Failed to connect to server." });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (!f) return;

    if (activeTab === "manual") {
      if (f.type.startsWith("image/")) postNotebook(f);
      else setFlash({ kind: "error", text: "Please upload an image for handwriting extraction." });
    } else {
      postSpreadsheet(f, activeTab);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-area">
        <Topbar onSearch={() => {}} title="Import Data" />

        <div className="content-wrapper">
          <div className="welcome-banner" style={{ marginBottom: 40 }}>
            <div className="welcome-text">
              <h2 style={{ fontSize: 32, marginBottom: 8 }}>Bring your data in.</h2>
              <p style={{ color: "var(--text-muted)", fontSize: 16 }}>
                Select your preferred method to sync your latest business records.
              </p>
            </div>
          </div>

          {flash && (
            <div
              style={{
                marginBottom: 24,
                padding: "16px 20px",
                borderRadius: 12,
                background: flash.kind === "success" ? "#ECFDF5" : "#FEF2F2",
                color: flash.kind === "success" ? "#065F46" : "#991B1B",
                border: `1px solid ${flash.kind === "success" ? "#10B981" : "#EF4444"}40`,
                fontSize: 14,
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 10,
                animation: "fadeInUp 0.4s ease",
              }}
            >
              {flash.kind === "success" ? "✅" : "⚠️"} {flash.text}
            </div>
          )}

          <div className="import-tabs-nav">
            <button
              className={`import-tab-btn ${activeTab === "excel" ? "active" : ""}`}
              onClick={() => setActiveTab("excel")}
            >
              Excel/Sheets
            </button>
            <button
              className={`import-tab-btn ${activeTab === "accounting" ? "active" : ""}`}
              onClick={() => setActiveTab("accounting")}
            >
              App like Tally/Zoho
            </button>
            <button
              className={`import-tab-btn ${activeTab === "manual" ? "active" : ""}`}
              onClick={() => setActiveTab("manual")}
            >
              Notebook/Manual
            </button>
            <button
              className={`import-tab-btn ${activeTab === "none" ? "active" : ""}`}
              onClick={() => router.push("/")}
            >
              Don&apos;t track
            </button>
          </div>

          {activeTab === "manual" ? (
            <div className="manual-upload-container">
              {previewData ? (
                <div className="preview-container animate-fadeInUp">
                  <h3 className="section-title">Preview Extracted Data</h3>
                  <div className="preview-table-wrapper">
                    <table className="preview-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>Type</th>
                          <th>Category</th>
                          <th>Amount</th>
                          <th>Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewData.map((row, idx) => (
                          <tr key={idx}>
                            <td>{row.date}</td>
                            <td>{row.type}</td>
                            <td>{row.category}</td>
                            <td>{row.amount}</td>
                            <td>{row.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="preview-actions">
                    <button className="import-btn-secondary" onClick={() => setPreviewData(null)} disabled={uploading}>
                      Cancel & Retry
                    </button>
                    <button className="import-btn-primary" onClick={handleConfirmNotebook} disabled={uploading}>
                      {uploading ? "Saving..." : "Confirm & Save"}
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="manual-upload-tagline">
                    &quot;No problem! Take a photo of your latest ledger entries and our AI will extract the data for you.&quot;
                  </p>

                  <div
                    className={`manual-drop-zone ${isDragging ? "drag-over" : ""}`}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={handleDrop}
                    onClick={() => imageRef.current?.click()}
                  >
                    <div className="camera-icon-wrapper">
                      <CameraIcon size={48} />
                    </div>
                    <span className="upload-text-main">
                      {uploading ? "Analyzing Handwriting..." : "Upload Image of Notebook"}
                    </span>
                    <p style={{ color: "#64748B", marginTop: 12, fontSize: 13 }}>Drag & drop or Click to browse</p>
                    <input
                      ref={imageRef}
                      type="file"
                      accept="image/*"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) postNotebook(f);
                      }}
                    />
                  </div>
                </>
              )}

              <div style={{ marginTop: 40, width: "100%", maxWidth: 800 }}>
                <h4 style={{ color: "white", marginBottom: 16, fontSize: 15 }}>How it works</h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20 }}>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 16, borderRadius: 12 }}>
                    <div style={{ color: "#F97316", fontWeight: 600, marginBottom: 8, fontSize: 12 }}>STEP 1</div>
                    <p style={{ color: "#94A3B8", fontSize: 13 }}>
                      Snap a clear photo of your handwritten ledger page.
                    </p>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 16, borderRadius: 12 }}>
                    <div style={{ color: "#3B82F6", fontWeight: 600, marginBottom: 8, fontSize: 12 }}>STEP 2</div>
                    <p style={{ color: "#94A3B8", fontSize: 13 }}>
                      Our Vision AI identifies dates, amounts and categories.
                    </p>
                  </div>
                  <div style={{ background: "rgba(255,255,255,0.03)", padding: 16, borderRadius: 12 }}>
                    <div style={{ color: "#10B981", fontWeight: 600, marginBottom: 8, fontSize: 12 }}>STEP 3</div>
                    <p style={{ color: "#94A3B8", fontSize: 13 }}>
                      Transactions appear in your dashboard instantly.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="import-card-grid" style={{ animation: "fadeInUp 0.5s ease" }}>
              <div
                className="import-method-card"
                style={{ borderStyle: isDragging ? "dashed" : "solid" }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
              >
                <div style={{ marginBottom: 20 }}>
                  {activeTab === "excel" ? (
                    <BarChartIcon size={32} color="#10B981" />
                  ) : (
                    <ReceiptIcon size={32} color="#3B82F6" />
                  )}
                </div>
                <h3 style={{ fontSize: 20, marginBottom: 12 }}>
                  {activeTab === "excel" ? "Spreadsheet Upload" : "Accounting Software Export"}
                </h3>
                <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
                  Drop your exported .csv or .xlsx file here to sync transactions. Ensure you have &apos;date&apos; and &apos;amount&apos;
                  columns.
                </p>

                <input
                  ref={activeTab === "excel" ? excelRef : exportRef}
                  type="file"
                  accept=".csv,.xlsx"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) postSpreadsheet(f, activeTab);
                  }}
                />

                <button
                  className="import-btn-primary"
                  onClick={() => (activeTab === "excel" ? excelRef : exportRef).current?.click()}
                  disabled={uploading}
                >
                  {uploading ? "Importing..." : "Choose File"}
                </button>
              </div>

              <div className="import-guide-box">
                <h3 style={{ fontSize: 18, marginBottom: 16 }}>Column Requirements</h3>
                <ul style={{ color: "var(--text-secondary)", fontSize: 14, display: "grid", gap: 12 }}>
                  <li>
                    <strong>Required:</strong> Date, Amount
                  </li>
                  <li>
                    <strong>Recommended:</strong> Type, Category, Description
                  </li>
                  <li>
                    <strong>Supported formats:</strong> .CSV, .XLSX
                  </li>
                </ul>
                <button
                  onClick={() => {
                    const csv = `date,type,category,amount,description\n2026-01-20,Revenue,Sales,1500.00,Sample Product sales`;
                    const blob = new Blob([csv], { type: "text/csv" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "sample_transactions.csv";
                    a.click();
                  }}
                  style={{
                    marginTop: 24,
                    padding: "8px 14px",
                    borderRadius: 8,
                    border: "1px solid var(--border-color)",
                    background: "white",
                    cursor: "pointer",
                    fontSize: 13,
                  }}
                >
                  Download Sample CSV
                </button>
              </div>
            </div>
          )}

          <div style={{ marginTop: 28, display: "flex", justifyContent: "center" }}>
            <Link href="/" className="import-back-link">
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

