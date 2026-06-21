import React from 'react';
import { Button } from '@patternfly/react-core';

// Example component showing the fix for Audit 350
const RecentTransactions: React.FC = () => {
  return (
    <div>
      {/* Before fix (buggy): */}
      {/* <Button variant="plain" icon={<ChevronDownIcon />} /> */}

      {/* After fix (corrected): */}
      <Button
        variant="plain"
        icon={<ChevronDownIcon />}
        aria-label="View recent transactions"
      />
    </div>
  );
};

export default RecentTransactions;