import React from 'react';
import { Button } from '@patternfly/react-core';

// Example component snippet showing the fix
const RecentTransactions: React.FC = () => {
  return (
    <div>
      {/* Before fix (buggy): */}
      {/* <Button variant="plain" icon={<Icon name="chevron-right" />} /> */}

      {/* After fix (corrected): */}
      <Button
        variant="plain"
        icon={<Icon name="chevron-right" />}
        aria-label="View more recent transactions"
      />
    </div>
  );
};

export default RecentTransactions;