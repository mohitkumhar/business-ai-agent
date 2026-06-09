/**
 * apiClient.js – API/Networking helper functions
 * Extracted from dashboard.js for focused API communication
 */

/**
 * Generic JSON fetch with error handling
 * @param {string} url - The API endpoint URL
 * @returns {Promise<Object|null>} Parsed JSON response or null on error
 */
async function fetchJSON(url) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  } catch (err) {
    console.error(`Failed to fetch ${url}:`, err);
    return null;
  }
}

/**
 * Fetch KPI summary data
 * @returns {Promise<Object|null>}
 */
async function fetchKPISummary() {
  return fetchJSON("/api/dashboard/summary");
}

/**
 * Fetch revenue vs expense data
 * @returns {Promise<Object|null>}
 */
async function fetchRevenueExpense() {
  return fetchJSON("/api/dashboard/revenue-vs-expense");
}

/**
 * Fetch transactions by category data
 * @returns {Promise<Object|null>}
 */
async function fetchTransactionsByCategory() {
  return fetchJSON("/api/dashboard/transactions-by-category");
}

/**
 * Fetch sales trend data
 * @returns {Promise<Object|null>}
 */
async function fetchSalesTrend() {
  return fetchJSON("/api/dashboard/sales-trend");
}

/**
 * Fetch alerts by severity data
 * @returns {Promise<Object|null>}
 */
async function fetchAlertsBySeverity() {
  return fetchJSON("/api/dashboard/alerts-by-severity");
}

/**
 * Fetch financial overview data
 * @returns {Promise<Object|null>}
 */
async function fetchFinancialOverview() {
  return fetchJSON("/api/dashboard/financial-overview");
}

/**
 * Fetch top products data
 * @returns {Promise<Object|null>}
 */
async function fetchTopProducts() {
  return fetchJSON("/api/dashboard/top-products");
}

/**
 * Fetch health scores data
 * @returns {Promise<Object|null>}
 */
async function fetchHealthScores() {
  return fetchJSON("/api/dashboard/health-scores");
}

/**
 * Fetch employee stats data
 * @returns {Promise<Object|null>}
 */
async function fetchEmployeeStats() {
  return fetchJSON("/api/dashboard/employee-stats");
}

export {
  fetchJSON,
  fetchKPISummary,
  fetchRevenueExpense,
  fetchTransactionsByCategory,
  fetchSalesTrend,
  fetchAlertsBySeverity,
  fetchFinancialOverview,
  fetchTopProducts,
  fetchHealthScores,
  fetchEmployeeStats,
};
