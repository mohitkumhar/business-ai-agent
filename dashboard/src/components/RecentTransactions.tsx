"use client";
import { useEffect, useState, useCallback } from "react";
import { api, Transaction } from "@/lib/api";
import { useDashboardPeriod } from "@/context/DashboardPeriodContext";
import { SearchIcon, FilterIcon } from "./Icons";

interface RecentTransactionsProps {
  search?: string;
}

export default function RecentTransactions({ search: globalSearch }: RecentTransactionsProps) {
  const { period, dataVersion } = useDashboardPeriod();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [localSearch, setLocalSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");

  const activeSearch = globalSearch || localSearch;

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await api.getRecentTransactions({
        search: activeSearch || undefined,
        category: selectedCategory || undefined,
        limit: 10,
        period,
      });
      setTransactions(res.transactions);
    } catch (err) {
      console.error("Failed to fetch transactions:", err);
    } finally {
      setLoading(false);
    }
  }, [activeSearch, selectedCategory, period, dataVersion]);

  useEffect(() => {
    api.getCategories()
      .then((res) => setCategories(res.categories))
      .catch(console.error);
  }, [dataVersion]);

  useEffect(() => {
    setLoading(true);
    const timer = setTimeout(() => {
      fetchTransactions();
    }, 300); // debounce search
    return () => clearTimeout(timer);
  }, [fetchTransactions]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`;
  };

  return (
    <div className="table-card">
      <div className="table-header">
        <h3 className="table-title">Recent Sales</h3>
        <div className="table-controls">
          <div className="table-search">
            <SearchIcon size={15} color="var(--text-muted)" />
            <input
              type="text"
              placeholder="Search"
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
            />
          </div>
          <select
            className="category-select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="">All Category</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <button className="filter-btn-icon">
            <FilterIcon size={14} /> Filter
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-spinner">Loading transactions...</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Txn ID</th>
              <th>Date</th>
              <th>Description</th>
              <th>Category</th>
              <th>Type</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--text-muted)", padding: 32 }}>
                  No transactions found
                </td>
              </tr>
            ) : (
              transactions.map((txn) => (
                <tr key={txn.transaction_id}>
                  <td style={{ fontWeight: 500 }}>#{txn.transaction_id}</td>
                  <td>{formatDate(txn.transaction_date)}</td>
                  <td style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {txn.description || "—"}
                  </td>
                  <td>{txn.category}</td>
                  <td>
                    <span className={`status-badge ${txn.type.toLowerCase()}`}>
                      {txn.type}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    ₹{txn.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
