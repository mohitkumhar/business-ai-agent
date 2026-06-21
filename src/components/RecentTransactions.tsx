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
        {/* Icon or visual element */}
        <span className="pf-c-icon pf-m-icon pf-m-lg" aria-hidden="true">
          <i className="icon-filter" />
        </span>
      </Button>

      {/* ... (remaining JSX) */}
    </div>
  );
};

export default RecentTransactions;