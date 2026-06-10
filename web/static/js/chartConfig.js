/**
 * chartConfig.js – Reusable Chart.js configuration and builders
 * Extracted from dashboard.js for consistency and reusability
 */

import { rgba, COLORS } from "./colorHelpers.js";
import { currency } from "./formatters.js";

/**
 * Initialize Chart.js global defaults
 */
function initializeChartDefaults() {
  Chart.defaults.color = "#9ea2b8";
  Chart.defaults.borderColor = "rgba(46,49,72,0.5)";
  Chart.defaults.font.family = "'Inter', sans-serif";
}

/**
 * Common tooltip callback for currency formatting
 * @returns {string} Formatted tooltip label
 */
const currencyTooltip = {
  callbacks: {
    label: (ctx) => `${ctx.dataset.label}: ${currency(ctx.parsed.y)}`,
  },
};

/**
 * Common Y-axis configuration for currency scales
 */
const currencyYAxis = {
  beginAtZero: true,
  ticks: { callback: (v) => currency(v) },
  grid: { color: "rgba(46,49,72,0.3)" },
};

/**
 * Common X-axis configuration
 */
const commonXAxis = {
  grid: { display: false },
};

/**
 * Build bar chart options
 * @param {Object} options - Custom options to merge
 * @returns {Object} Complete chart options
 */
function buildBarChartOptions(options = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "top" },
      tooltip: currencyTooltip,
    },
    scales: {
      y: currencyYAxis,
      x: commonXAxis,
    },
    ...options,
  };
}

/**
 * Build line chart options
 * @param {Object} options - Custom options to merge
 * @returns {Object} Complete chart options
 */
function buildLineChartOptions(options = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "top" },
      tooltip: currencyTooltip,
    },
    scales: {
      y: currencyYAxis,
      x: commonXAxis,
    },
    ...options,
  };
}

/**
 * Build pie/doughnut chart options
 * @param {Object} options - Custom options to merge
 * @returns {Object} Complete chart options
 */
function buildPieChartOptions(options = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: "bottom", labels: { padding: 12 } },
    },
    ...options,
  };
}

/**
 * Build radar chart options
 * @param {Object} options - Custom options to merge
 * @returns {Object} Complete chart options
 */
function buildRadarChartOptions(options = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        angleLines: { color: "rgba(46,49,72,0.4)" },
        grid: { color: "rgba(46,49,72,0.3)" },
        pointLabels: { font: { size: 11 } },
      },
    },
    plugins: {
      legend: { position: "bottom", labels: { padding: 10 } },
    },
    ...options,
  };
}

export {
  initializeChartDefaults,
  currencyTooltip,
  currencyYAxis,
  commonXAxis,
  buildBarChartOptions,
  buildLineChartOptions,
  buildPieChartOptions,
  buildRadarChartOptions,
};
