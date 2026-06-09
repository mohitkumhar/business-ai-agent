/**
 * formatters.js – Data formatting utilities
 * Extracted from dashboard.js for reusability
 */

/**
 * Format a number as currency (USD)
 * @param {number|string} n - The number to format
 * @returns {string} Formatted currency string (e.g., "$1,234,567")
 */
function currency(n) {
  return (
    "$" +
    Number(n).toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    })
  );
}

/**
 * Format a number with comma separators
 * @param {number|string} n - The number to format
 * @returns {string} Formatted number string
 */
function formatNumber(n) {
  return Number(n).toLocaleString("en-US");
}

/**
 * Format a percentage value
 * @param {number} value - The value to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted percentage string
 */
function formatPercent(value, decimals = 2) {
  return Number(value).toFixed(decimals) + "%";
}

export { currency, formatNumber, formatPercent };
