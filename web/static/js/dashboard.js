/**
 * dashboard.js – Main orchestrator for dashboard charts and KPI rendering
 *
 * This module is refactored from a 423-line monolith into focused components:
 * - Separated concerns: API calls, rendering, colors, formatting, chart configs
 * - Each chart type has its own focused component for easier maintenance
 * - Tests can target specific functionality without entangled dependencies
 *
 * For backward compatibility with traditional script loading, this file uses
 * dynamic imports or global namespace. See index.html for proper script setup.
 */

// Dynamic imports for modular architecture
Promise.all([
  import("./chartConfig.js"),
  import("./kpiCard.js"),
  import("./revenueExpenseChart.js"),
  import("./transactionsPieChart.js"),
  import("./salesTrendChart.js"),
  import("./alertsSeverityChart.js"),
  import("./financialOverviewChart.js"),
  import("./topProductsChart.js"),
  import("./healthScoresChart.js"),
  import("./employeeStatsChart.js"),
])
  .then((modules) => {
    "use strict";

    const [
      chartConfig,
      kpiCard,
      revenueExpenseChart,
      transactionsPieChart,
      salesTrendChart,
      alertsSeverityChart,
      financialOverviewChart,
      topProductsChart,
      healthScoresChart,
      employeeStatsChart,
    ] = modules;

    // Initialize Chart.js defaults once at startup
    chartConfig.initializeChartDefaults();

    /**
     * Initialize and load all dashboard components in parallel
     * @returns {Promise<void>}
     */
    async function init() {
      try {
        // Load all charts in parallel for better performance
        const results = await Promise.all([
          kpiCard.loadKPI(),
          revenueExpenseChart.loadRevenueExpense(),
          transactionsPieChart.loadTransactionsPie(),
          salesTrendChart.loadSalesTrend(),
          alertsSeverityChart.loadAlertsSeverity(),
          financialOverviewChart.loadFinancialOverview(),
          topProductsChart.loadTopProducts(),
          healthScoresChart.loadHealthScores(),
          employeeStatsChart.loadEmployeeStats(),
        ]);

        // Log any failures (for debugging)
        const failed = results
          .map((result, index) => ({ index, result }))
          .filter(({ result }) => result === false)
          .map(({ index }) => {
            const names = [
              "KPI",
              "RevenueExpense",
              "TransactionsPie",
              "SalesTrend",
              "AlertsSeverity",
              "FinancialOverview",
              "TopProducts",
              "HealthScores",
              "EmployeeStats",
            ];
            return names[index];
          });

        if (failed.length > 0) {
          console.warn("Failed to load charts:", failed);
        }
      } catch (err) {
        console.error("Dashboard initialization error:", err);
      }
    }

    // Initial load
    init();

    // Auto-refresh every 60 seconds
    setInterval(init, 60000);
  })
  .catch((err) => {
    console.error("Failed to load dashboard modules:", err);
    console.error(
      "Make sure all chart component files are in the same directory as dashboard.js",
    );
  });
