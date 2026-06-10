/**
 * colorHelpers.js – Color palette and theme utilities
 * Extracted from dashboard.js for reusability and maintainability
 */

const COLORS = {
  blue: "#5b8af5",
  green: "#4ecb71",
  red: "#f55b6a",
  orange: "#f5a623",
  purple: "#a855f7",
  cyan: "#22d3ee",
  pink: "#ec4899",
  lime: "#84cc16",
};

const PALETTE = Object.values(COLORS);

/**
 * Converts a hex color to RGBA format
 * @param {string} hex - Hex color code (e.g., "#5b8af5")
 * @param {number} alpha - Alpha value (0-1)
 * @returns {string} RGBA color string
 */
function rgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/**
 * Color mapping for alert severity levels
 */
const SEVERITY_COLORS = {
  Low: COLORS.green,
  Medium: COLORS.orange,
  High: COLORS.red,
};

/**
 * Color mapping for employee status
 */
const STATUS_COLORS = {
  Active: COLORS.green,
  Left: COLORS.red,
};

/**
 * Get color for severity level
 * @param {string} severity - Severity level (Low, Medium, High)
 * @returns {string} Hex color code
 */
function getSeverityColor(severity) {
  return SEVERITY_COLORS[severity] || COLORS.purple;
}

/**
 * Get color for status
 * @param {string} status - Status (Active, Left, etc.)
 * @returns {string} Hex color code
 */
function getStatusColor(status) {
  return STATUS_COLORS[status] || COLORS.purple;
}

export {
  COLORS,
  PALETTE,
  rgba,
  SEVERITY_COLORS,
  STATUS_COLORS,
  getSeverityColor,
  getStatusColor,
};
