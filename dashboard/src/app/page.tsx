"use client";
import { useState } from "react";

import { DashboardPeriodProvider } from "@/context/DashboardPeriodContext";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import WelcomeBanner from "@/components/WelcomeBanner";
import KPICards from "@/components/KPICards";
import RevenueVsExpenses from "@/components/RevenueVsExpenses";
import TransactionsByCategory from "@/components/TransactionsByCategory";
import SalesTrend from "@/components/SalesTrend";
import AlertsBySeverity from "@/components/AlertsBySeverity";
import RevenueInsights from "@/components/RevenueInsights";
import SalesOverview from "@/components/SalesOverview";
import TopProducts from "@/components/TopProducts";
import HealthScores from "@/components/HealthScores";
import EmployeeStatistics from "@/components/EmployeeStatistics";
import RecentTransactions from "@/components/RecentTransactions";
import ForecastChart from "@/components/ForecastChart";
import ErrorBoundary from "@/components/ErrorBoundary";

import { useEffect } from "react";

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    // Auth bypass for demo
    // localStorage.setItem("profit_pilot_token", "demo-token");
  }, []);

  return (
    <DashboardPeriodProvider>
      <div className="app-layout">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="main-area">
          <Topbar
            onSearch={setSearchQuery}
            onMenuClick={() => setSidebarOpen(true)}
          />
          <div className="content-wrapper">
            <WelcomeBanner />
            <ErrorBoundary label="KPI cards">
              <KPICards />
            </ErrorBoundary>

            {/* Row 1: Revenue vs Expenses + Transactions by Category */}
            <div className="charts-row pt-4">
              <ErrorBoundary label="Revenue vs expenses">
                <RevenueVsExpenses />
              </ErrorBoundary>
              <ErrorBoundary label="Transactions by category">
                <TransactionsByCategory />
              </ErrorBoundary>
            </div>

            {/* Row 2: Sales Trend + Alerts by Severity */}
            <div className="charts-row">
              <ErrorBoundary label="Sales trend">
                <SalesTrend />
              </ErrorBoundary>
              <ErrorBoundary label="Alerts by severity">
                <AlertsBySeverity />
              </ErrorBoundary>
            </div>

            {/* Row 2.5: AI Revenue Forecast */}
            <div className="charts-row" style={{ gridTemplateColumns: "1fr" }}>
              <ErrorBoundary label="Revenue forecast">
                <ForecastChart />
              </ErrorBoundary>
            </div>


            {/* Row 3: Financial Overview + Top Products */}
            <div className="charts-row">
              <ErrorBoundary label="Revenue insights">
                <RevenueInsights />
              </ErrorBoundary>
              <ErrorBoundary label="Top products">
                <TopProducts />
              </ErrorBoundary>
            </div>

            {/* Row 4: Health Scores + Employee Statistics */}
            <div className="charts-row">
              <ErrorBoundary label="Health scores">
                <HealthScores />
              </ErrorBoundary>
              <ErrorBoundary label="Employee statistics">
                <EmployeeStatistics />
              </ErrorBoundary>
            </div>

            {/* Row 5: Sales Overview (gauge) — full width */}
            <div className="charts-row" style={{ gridTemplateColumns: "1fr" }}>
              <ErrorBoundary label="Sales overview">
                <SalesOverview />
              </ErrorBoundary>
            </div>

            {/* Row 6: Recent Transactions */}
            <ErrorBoundary label="Recent transactions">
              <RecentTransactions search={searchQuery} />
            </ErrorBoundary>
          </div>
        </div>
      </div>
    </DashboardPeriodProvider>
  );
}
