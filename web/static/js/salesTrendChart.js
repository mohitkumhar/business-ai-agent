/**
 * salesTrendChart.js – Sales Trend line chart
 */

import { fetchSalesTrend } from "./apiClient.js";
import { rgba, COLORS } from "./colorHelpers.js";
import { buildLineChartOptions } from "./chartConfig.js";

/**
 * Load and render Sales Trend chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadSalesTrend() {
  const data = await fetchSalesTrend();
  if (!data || data.error) return false;

  new Chart(document.getElementById("salesTrendChart"), {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Revenue",
          data: data.revenue,
          borderColor: COLORS.blue,
          backgroundColor: rgba(COLORS.blue, 0.1),
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
        {
          label: "Expenses",
          data: data.expenses,
          borderColor: COLORS.red,
          backgroundColor: rgba(COLORS.red, 0.1),
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    },
    options: buildLineChartOptions(),
  });

  return true;
}

export { loadSalesTrend };
