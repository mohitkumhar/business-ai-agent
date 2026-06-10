/**
 * topProductsChart.js – Top Products horizontal bar chart
 */

import { fetchTopProducts } from "./apiClient.js";
import { rgba, COLORS } from "./colorHelpers.js";

/**
 * Load and render Top Products chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadTopProducts() {
  const data = await fetchTopProducts();
  if (!data || data.error) return false;

  new Chart(document.getElementById("topProductsChart"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Stock Qty",
          data: data.stock,
          backgroundColor: rgba(COLORS.cyan, 0.7),
          borderColor: COLORS.cyan,
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Profit Margin ($)",
          data: data.margin,
          backgroundColor: rgba(COLORS.green, 0.7),
          borderColor: COLORS.green,
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: { color: "rgba(46,49,72,0.3)" },
        },
        y: {
          grid: { display: false },
        },
      },
    },
  });

  return true;
}

export { loadTopProducts };
