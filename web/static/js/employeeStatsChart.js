/**
 * employeeStatsChart.js – Employee Statistics dual-axis chart
 */

import { fetchEmployeeStats } from "./apiClient.js";
import { rgba, COLORS, getStatusColor } from "./colorHelpers.js";
import { currency } from "./formatters.js";

/**
 * Load and render Employee Stats chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadEmployeeStats() {
  const data = await fetchEmployeeStats();
  if (!data || data.error) return false;

  new Chart(document.getElementById("employeeStatsChart"), {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Count",
          data: data.counts,
          backgroundColor: data.labels.map((l) => rgba(getStatusColor(l), 0.7)),
          borderColor: data.labels.map((l) => getStatusColor(l)),
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y",
        },
        {
          label: "Avg Salary ($)",
          data: data.avg_salary,
          backgroundColor: data.labels.map(() => rgba(COLORS.cyan, 0.5)),
          borderColor: data.labels.map(() => COLORS.cyan),
          borderWidth: 1,
          borderRadius: 6,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
      },
      scales: {
        y: {
          beginAtZero: true,
          position: "left",
          title: { display: true, text: "Count" },
          grid: { color: "rgba(46,49,72,0.3)" },
        },
        y1: {
          beginAtZero: true,
          position: "right",
          title: { display: true, text: "Avg Salary" },
          grid: { display: false },
          ticks: { callback: (v) => currency(v) },
        },
        x: {
          grid: { display: false },
        },
      },
    },
  });

  return true;
}

export { loadEmployeeStats };
