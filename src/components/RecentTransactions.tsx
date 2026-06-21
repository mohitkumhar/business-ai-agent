import React from 'react';
import { Button } from '@patternfly/react-core';

// Example component showing the fix for Audit 350
const RecentTransactions: React.FC = () => {
  return (
    <div>
      {/* Before fix: relied solely on icon, no accessible name */}
      {/* <Button variant="plain" icon={<SomeIcon />} /> */}

      {/* After fix: added accessible name */}
      <Button
        variant="plain"
        icon={<SomeIcon />}
        aria-label="Filter transactions by date range"
      />
    </div>
  );
};

export default RecentTransactions;