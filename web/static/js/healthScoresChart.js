/**
 * healthScoresChart.js – Health Scores radar chart
 */

import { fetchHealthScores } from "./apiClient.js";
import { rgba, PALETTE } from "./colorHelpers.js";
import { buildRadarChartOptions } from "./chartConfig.js";

/**
 * Load and render Health Scores radar chart
 * @returns {Promise<boolean>} True if successful, false otherwise
 */
async function loadHealthScores() {
  const data = await fetchHealthScores();
  if (!data || data.error || !data.scores.length) return false;

  const labels = [
    "Overall",
    "Cash",
    "Profitability",
    "Growth",
    "Cost Control",
    "Risk",
  ];
  const datasets = data.scores.map((s, i) => ({
    label: s.name,
    data: [
      s.overall,
      s.cash,
      s.profitability,
      s.growth,
      s.cost_control,
      s.risk,
    ],
    borderColor: PALETTE[i % PALETTE.length],
    backgroundColor: rgba(PALETTE[i % PALETTE.length], 0.1),
    pointBackgroundColor: PALETTE[i % PALETTE.length],
    pointRadius: 3,
  }));

  new Chart(document.getElementById("healthScoresChart"), {
    type: "radar",
    data: { labels, datasets },
    options: buildRadarChartOptions(),
  });

  return true;
}

export { loadHealthScores };
