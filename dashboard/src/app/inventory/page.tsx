"use client";
import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { api, TopProducts as TopProductsData } from "@/lib/api";
import { PackageIcon } from "@/components/Icons";

import { DashboardPeriodProvider } from "@/context/DashboardPeriodContext";

export default function InventoryPage() {
  const [data, setData] = useState<TopProductsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTopProducts()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardPeriodProvider>
      <div className="app-layout">
        <Sidebar />
        <div className="main-area">
          <Topbar onSearch={() => {}} />
          <div className="content-wrapper">
            <div className="welcome-banner">
              <div className="welcome-text">
                <h2>Inventory & Stock</h2>
                <p>Manage your products and monitor stock levels</p>
              </div>
            </div>

            <div className="table-card mt-6">
              <div className="table-header">
                <h3 className="table-title">Products Inventory</h3>
              </div>

              {loading ? (
                <div className="loading-spinner">Loading inventory...</div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Product Name</th>
                      <th>Stock Quantity</th>
                      <th>Profit Margin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.labels.map((name, i) => (
                      <tr key={name}>
                        <td style={{ fontWeight: 500 }}>
                          <div className="flex items-center gap-2">
                            <PackageIcon size={16} color="var(--accent-blue)" />
                            {name}
                          </div>
                        </td>
                        <td>
                          <span className={`status-badge ${data.stock[i] < 20 ? 'expense' : 'revenue'}`}>
                            {data.stock[i]} units
                          </span>
                        </td>
                        <td style={{ fontWeight: 600 }}>
                          ${(data.margin_amount?.[i] ?? data.margin[i]).toLocaleString(
                            undefined,
                            { minimumFractionDigits: 2 }
                          )}
                          {typeof data.margin_pct?.[i] === "number" && (
                            <span style={{ color: "var(--text-secondary)", fontSize: 12, marginLeft: 8 }}>
                              ({data.margin_pct[i].toFixed(1)}%)
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardPeriodProvider>
  );
}
