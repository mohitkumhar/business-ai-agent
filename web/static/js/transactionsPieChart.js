/**
 * transactionsPieChart.js – Transactions by Category pie chart
 */

import { fetchTransactionsByCategory } from "./apiClient.js";
import { PALETTE } from "./colorHelpers.js";
import { buildPieChartOptions } from "./chartConfig.js";

/**
 * Load and render Transactions by Category pie chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadTransactionsPie() {
  const data = await fetchTransactionsByCategory();
  if (!data || data.error) return false;

  new Chart(document.getElementById("transactionsPieChart"), {
    type: "pie",
    data: {
      labels: data.labels,
      datasets: [
        {
          data: data.data,
          backgroundColor: PALETTE.slice(0, data.labels.length),
          borderWidth: 0,
        },
      ],
    },
    options: buildPieChartOptions(),
  });

  return true;
}

export { loadTransactionsPie };
