import React from 'react';

const RecentTransactions = () => {
  return (
    <div className="recent-transactions">
      <h2>Recent Transactions</h2>
      <button
        aria-label="Filter transactions by date range"
        className="visual-icon-button"
        title="Filter transactions by date range"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none">
          <path d="M10 14H14V18H10V14Z" fill="#333" />
          <path d="M4 10H20V14H4V10Z" fill="#333" />
        </svg>
      </button>
      {/* ... rest of component */}
    </div>
  );
};

export default RecentTransactions;