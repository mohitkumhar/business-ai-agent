/**
 * alertsSeverityChart.js – Alerts by Severity doughnut chart
 */

import { fetchAlertsBySeverity } from "./apiClient.js";
import { getSeverityColor, PALETTE } from "./colorHelpers.js";
import { buildPieChartOptions } from "./chartConfig.js";

/**
 * Load and render Alerts by Severity chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadAlertsSeverity() {
  const data = await fetchAlertsBySeverity();
  if (!data || data.error) return false;

  new Chart(document.getElementById("alertsSeverityChart"), {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [
        {
          data: data.data,
          backgroundColor: data.labels.map((label) => getSeverityColor(label)),
          borderWidth: 0,
        },
      ],
    },
    options: buildPieChartOptions({ cutout: "55%" }),
  });

  return true;
}

export { loadAlertsSeverity };
