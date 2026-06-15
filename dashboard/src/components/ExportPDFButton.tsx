"use client";

import React, { useState } from "react";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { ExportIcon, XIcon } from "./Icons";

const AVAILABLE_WIDGETS = [
  { id: "kpi-cards", label: "KPI Cards" },
  { id: "revenue-vs-expenses", label: "Revenue vs Expenses" },
  { id: "transactions-by-category", label: "Transactions by Category" },
  { id: "sales-trend", label: "Sales Trend" },
  { id: "alerts-severity", label: "Alerts by Severity" },
  { id: "revenue-forecast", label: "AI Revenue Forecast" },
  { id: "revenue-insights", label: "Revenue Insights" },
  { id: "top-products", label: "Top Products" },
  { id: "health-scores", label: "Health Scores" },
  { id: "employee-stats", label: "Employee Statistics" },
  { id: "sales-overview", label: "Sales Overview" },
  { id: "recent-transactions", label: "Recent Transactions" },
];

export default function ExportPDFButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedWidgets, setSelectedWidgets] = useState<string[]>(
    AVAILABLE_WIDGETS.map((w) => w.id)
  );

  const toggleWidget = (id: string) => {
    setSelectedWidgets((prev) =>
      prev.includes(id) ? prev.filter((w) => w !== id) : [...prev, id]
    );
  };

  const handleExport = async () => {
    if (selectedWidgets.length === 0) return;
    
    setIsExporting(true);
    try {
      const pdf = new jsPDF("p", "mm", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 10;
      const contentWidth = pageWidth - 2 * margin;
      
      let currentY = margin;

      // Add Header
      const businessName = "ProfitPilot AI Agent"; // Could be dynamic
      pdf.setFontSize(18);
      pdf.setTextColor(67, 56, 202); // indigo-700
      pdf.text(`Business Performance Report — ${businessName}`, margin, currentY + 10);
      
      pdf.setFontSize(10);
      pdf.setTextColor(100, 116, 139); // slate-500
      pdf.text(`Generated on ${new Date().toLocaleString()}`, margin, currentY + 18);
      
      currentY += 25;

      for (const widgetId of selectedWidgets) {
        const element = document.querySelector(`[data-widget-id="${widgetId}"]`) as HTMLElement;
        if (!element) continue;

        const canvas = await html2canvas(element, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: "#ffffff",
        });

        const imgData = canvas.toDataURL("image/png");
        const imgWidth = contentWidth;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;

        // Check if we need a new page
        if (currentY + imgHeight > pageHeight - margin) {
          pdf.addPage();
          currentY = margin;
        }

        pdf.addImage(imgData, "PNG", margin, currentY, imgWidth, imgHeight);
        currentY += imgHeight + 10;
      }

      // Add Footer with page numbers
      const pageCount = pdf.internal.pages.length - 1;
      for (let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.setTextColor(150);
        pdf.text(
          `Page ${i} of ${pageCount}`,
          pageWidth / 2,
          pageHeight - 5,
          { align: "center" }
        );
      }

      pdf.save(`ProfitPilot_Report_${new Date().toISOString().split("T")[0]}.pdf`);
      setIsOpen(false);
    } catch (error) {
      console.error("PDF Export failed:", error);
      alert("Failed to generate PDF. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <>
      <button
        className="topbar-icon-btn"
        onClick={() => setIsOpen(true)}
        title="Export Dashboard as PDF"
      >
        <ExportIcon size={16} />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Export Report</h3>
              <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-slate-600">
                <XIcon size={20} />
              </button>
            </div>

            <div className="px-6 py-4 max-h-[60vh] overflow-y-auto">
              <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
                Select the components you want to include in your PDF report.
              </p>
              <div className="space-y-2">
                {AVAILABLE_WIDGETS.map((widget) => (
                  <label
                    key={widget.id}
                    className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedWidgets.includes(widget.id)}
                      onChange={() => toggleWidget(widget.id)}
                      className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                      {widget.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/30 flex gap-3">
              <button
                onClick={() => setIsOpen(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExport}
                disabled={isExporting || selectedWidgets.length === 0}
                className="flex-1 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {isExporting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Generating...
                  </>
                ) : (
                  "Download PDF"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
