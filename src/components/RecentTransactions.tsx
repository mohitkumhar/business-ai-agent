import React from 'react';
import { Button } from '@patternfly/react-core';

// Example component showing the fix for audit 350
const RecentTransactions: React.FC = () => {
  return (
    <div>
      {/* Before fix (buggy): */}
      {/* <Button variant="plain" icon={IconExample} /> */}

      {/* After fix (corrected): */}
      <Button
        variant="plain"
        icon={IconExample}
        aria-label="Filter transactions by date range"
      />
    </div>
  );
};

export default RecentTransactions;