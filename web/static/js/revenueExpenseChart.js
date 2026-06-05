/**
 * revenueExpenseChart.js – Revenue vs Expense chart component
 */

import { fetchRevenueExpense } from "./apiClient.js";
import { rgba, COLORS } from "./colorHelpers.js";
import { buildBarChartOptions } from "./chartConfig.js";

/**
 * Load and render Revenue vs Expense chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadRevenueExpense() {
  const data = await fetchRevenueExpense();
  if (!data || data.error) return false;

  new Chart(document.getElementById("revenueExpenseChart"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Revenue",
          data: data.revenue,
          backgroundColor: rgba(COLORS.blue, 0.7),
          borderColor: COLORS.blue,
          borderWidth: 1,
          borderRadius: 6,
        },
        {
          label: "Expenses",
          data: data.expenses,
          backgroundColor: rgba(COLORS.red, 0.7),
          borderColor: COLORS.red,
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: buildBarChartOptions(),
  });

  return true;
}

export { loadRevenueExpense };
