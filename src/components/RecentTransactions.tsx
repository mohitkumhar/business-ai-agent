import React from 'react';
import { Button } from '@patternfly/react-core';

// ... (other imports and code)

const RecentTransactions: React.FC = () => {
  // ... (other code)

  return (
    <div>
      {/* ... (other elements) */}

      {/* Button with accessible name */}
      <Button
        aria-label="Filter transactions by date range"
        variant="plain"
      >
        <i className="fas fa-filter" />
      </Button>

      {/* ... (remaining JSX) */}
    </div>
  );
};

export default RecentTransactions;