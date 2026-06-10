/**
 * financialOverviewChart.js – Financial Overview mixed chart (bar + line)
 */

import { fetchFinancialOverview } from "./apiClient.js";
import { rgba, COLORS } from "./colorHelpers.js";
import { currency } from "./formatters.js";
import { buildBarChartOptions } from "./chartConfig.js";

/**
 * Load and render Financial Overview chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadFinancialOverview() {
  const data = await fetchFinancialOverview();
  if (!data || data.error) return false;

  new Chart(document.getElementById("financialOverviewChart"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          type: "line",
          label: "Net Profit",
          data: data.net_profit,
          borderColor: COLORS.green,
          backgroundColor: rgba(COLORS.green, 0.1),
          fill: false,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: "y",
          order: 0,
        },
        {
          label: "Revenue",
          data: data.revenue,
          backgroundColor: rgba(COLORS.blue, 0.6),
          borderRadius: 4,
          yAxisID: "y",
          order: 1,
        },
        {
          label: "Expenses",
          data: data.expenses,
          backgroundColor: rgba(COLORS.red, 0.6),
          borderRadius: 4,
          yAxisID: "y",
          order: 2,
        },
      ],
    },
    options: buildBarChartOptions({
      plugins: {
        legend: { position: "top" },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${currency(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: (v) => currency(v) },
          grid: { color: "rgba(46,49,72,0.3)" },
        },
        x: { grid: { display: false } },
      },
    }),
  });

  return true;
}

export { loadFinancialOverview };
