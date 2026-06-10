/**
 * kpiCard.js – KPI card data loading and rendering
 */

import { fetchKPISummary } from "./apiClient.js";
import { currency } from "./formatters.js";
import { COLORS } from "./colorHelpers.js";

/**
 * Load and render KPI cards
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadKPI() {
  const data = await fetchKPISummary();
  if (!data || data.error) return false;

  // Update KPI values
  document.getElementById("kpiRevenue").textContent = currency(
    data.total_revenue,
  );
  document.getElementById("kpiExpenses").textContent = currency(
    data.total_expenses,
  );
  document.getElementById("kpiProfit").textContent = currency(data.net_profit);
  document.getElementById("kpiTransactions").textContent =
    data.total_transactions;
  document.getElementById("kpiAlerts").textContent = data.active_alerts;

  // Color net profit based on value
  const profitEl = document.getElementById("kpiProfit");
  profitEl.style.color = data.net_profit >= 0 ? COLORS.green : COLORS.red;

  return true;
}

export { loadKPI };
